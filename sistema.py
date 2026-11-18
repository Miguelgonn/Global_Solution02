"""Citizen Assist AI - assistente de orientação cidadã (protótipo, interface de texto).
Executar:   python src/sistema.py            (menu interativo)
Testes:     python src/sistema.py --testes   (gera docs/resultados_testes.csv)
"""
import csv, json, os, re, sys, time, unicodedata

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(RAIZ, "data", "base_conhecimento.json")
TESTES = os.path.join(RAIZ, "data", "perguntas_teste.json")
OBRIGATORIOS = ["id", "tema", "palavras_chave", "orientacao", "referencia", "data_verificacao"]
STOP = set("a o as os um uma de do da dos das no na nos nas em para por com e ou que se ao aos meu minha "
           "eu como qual quais quero preciso posso onde quando saber sobre fazer ser pra pelo pela ter tem".split())
NAO_OFICIAL = "Protótipo educacional: não é atendimento oficial nem tem ligação com órgãos públicos."
CONFIRMAR = "Confirme requisitos, prazos e valores atuais na fonte oficial antes de agir."
MIN_PONTOS, MARGEM = 3, 1


# ---------- 1. Base de conhecimento ----------
def carregar(caminho=BASE):
    """Lê e valida o JSON. Retorna (temas, registros_por_id, avisos). Levanta ValueError se inutilizável."""
    if not os.path.isfile(caminho) or os.path.getsize(caminho) == 0:
        raise ValueError("arquivo da base ausente ou vazio")
    try:
        with open(caminho, encoding="utf-8") as f:
            dados = json.load(f)
        temas, lista = dados["temas"], dados["registros"]
    except (json.JSONDecodeError, KeyError, TypeError):
        raise ValueError("JSON inválido: esperado {'temas': {...}, 'registros': [...]}")
    regs, avisos = {}, []
    for i, r in enumerate(lista, 1):
        rid = r.get("id", f"#{i}") if isinstance(r, dict) else f"#{i}"
        faltam = [c for c in OBRIGATORIOS if not isinstance(r, dict) or c not in r]
        if faltam or r["tema"] not in temas or not r["palavras_chave"] or rid in regs:
            avisos.append(f"{rid} ignorado (campos ausentes/inválidos ou id repetido: {faltam or 'ver tema/palavras'})")
            continue
        if not r["data_verificacao"]:
            avisos.append(f"{rid}: sem data de verificação (ainda não conferido)")
        r.setdefault("subtema", "Geral"); r.setdefault("pergunta", ""); r.setdefault("requer_confirmacao", True)
        r["relacionados"] = r.get("relacionados", [])
        regs[rid] = r
    if not regs:
        raise ValueError("nenhum registro válido na base")
    for r in regs.values():                      # grafo simples: remove ligações para ids inexistentes
        r["relacionados"] = [x for x in r["relacionados"] if x in regs and x != r["id"]]
    return temas, regs, avisos


# ---------- 2. Busca por palavras-chave com pontuação ----------
def tokens(txt):
    txt = unicodedata.normalize("NFD", txt.lower())
    txt = re.sub(r"[^a-z0-9]+", " ", "".join(c for c in txt if unicodedata.category(c) != "Mn"))
    return [t[:-1] if len(t) > 3 and t.endswith("s") else t for t in txt.split() if t not in STOP and len(t) > 1]


def pontuar(q, r):
    """+4 por frase de palavra-chave inteira na consulta, +2 por palavra em palavra-chave,
    +1 por palavra na pergunta-modelo/subtema."""
    texto, palavras = " " + " ".join(q) + " ", set(q)
    frases = [" ".join(tokens(k)) for k in r["palavras_chave"]]
    kw = {t for f in frases for t in f.split()}
    extra = set(tokens(r["pergunta"] + " " + r["subtema"])) - kw
    pts = sum(4 + len(f.split()) - 1 for f in frases if f and f" {f} " in texto)
    return pts + 2 * len(palavras & kw) + len(palavras & extra)


def buscar(entrada, regs):
    """Retorna (status, resultados). Status: ok | ambigua | sem_correspondencia | vazia | invalida | dados_pessoais."""
    if not entrada or not entrada.strip():
        return "vazia", []
    if len(entrada) > 300:
        return "invalida", []
    if re.search(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", entrada):
        return "dados_pessoais", []
    q = tokens(entrada)
    if not q:
        return "invalida", []
    rank = sorted(((pontuar(q, r), r["id"]) for r in regs.values()), key=lambda x: (-x[0], x[1]))
    rank = [(p, regs[i]) for p, i in rank if p >= MIN_PONTOS]
    if not rank:
        return ("sem_correspondencia" if any(c.isalpha() for c in entrada) else "invalida"), []
    # empate entre os dois primeiros, de subtemas diferentes => ambígua (usuário escolhe)
    if len(rank) > 1 and rank[0][0] - rank[1][0] <= MARGEM and rank[0][1]["subtema"] != rank[1][1]["subtema"]:
        return "ambigua", [r for p, r in rank if rank[0][0] - p <= MARGEM][:4]
    return "ok", [r for _, r in rank[:4]]      # [0] = melhor, resto = alternativas


# ---------- 3. Modelos de resposta (instruções documentadas) ----------
MODELOS = {
    "A": "Direto - papel: guia breve | formato: orientação + fonte | regra: só usar a base, citar fonte.",
    "B": "Estruturado - papel: assistente NÃO oficial | formato: ASSUNTO/ORIENTAÇÃO/FONTE/DATA/AVISO | "
         "regras: só usar a base, citar fonte e data, avisar que não é oficial, destacar confirmação.",
}


def formatar(modelo, r):
    if modelo == "A":
        return "\n".join([r["orientacao"], f"Fonte: {r['referencia']}"] + ([f"Aviso: {CONFIRMAR}"] if r["requer_confirmacao"] else []))
    linhas = [f"ASSUNTO: {r['subtema']} ({r['id']})", f"ORIENTAÇÃO: {r['orientacao']}", f"FONTE: {r['referencia']}",
              f"VERIFICADO EM: {r['data_verificacao'] or 'pendente de conferência'}"]
    if r["requer_confirmacao"]:
        linhas.append(f"AVISO: {CONFIRMAR}")
    return "\n".join(linhas + [f"NOTA: {NAO_OFICIAL}"])


MENSAGENS = {
    "vazia": "Você não digitou nada. Escreva sua dúvida ou escolha um tema no menu.",
    "invalida": "Não entendi essa entrada. Use palavras simples sobre o assunto (ex.: 'carteira de trabalho').",
    "dados_pessoais": "Parece um número de documento. Por privacidade, não informe dados pessoais; reescreva sem eles.",
    "sem_correspondencia": "Não encontrei informação confiável sobre isso na base, então não vou arriscar uma resposta. "
                           "Reformule, escolha um tema no menu ou procure o órgão responsável.",
}


# ---------- 4. Interface de texto ----------
def ler(msg="> "):
    try:
        return input(msg).strip()
    except (EOFError, KeyboardInterrupt):
        print("\nEncerrando."); sys.exit(0)


def opcao(maximo):
    t = ler()
    if not t:
        print("Entrada vazia. Digite o número de uma opção."); return None
    if not t.isdigit() or int(t) > maximo:
        print(f"Opção inexistente: '{t}'. Escolha de 0 a {maximo}."); return None
    return int(t)


def mostrar(regs, modelo, r):
    """Exibe a orientação e permite navegar pelos assuntos relacionados."""
    while True:
        print("\n" + "-" * 60 + "\n" + formatar(modelo, r) + "\n" + "-" * 60)
        rel = [regs[i] for i in r["relacionados"]]
        if not rel:
            return
        print("Assuntos relacionados:")
        for n, x in enumerate(rel, 1):
            print(f"  {n}. {x['subtema']}: {x['pergunta']}")
        print("  0. Voltar ao menu")
        op = opcao(len(rel))
        if op == 0:
            return
        if op:
            r = rel[op - 1]


def escolher(titulo, itens, rotulo):
    print(f"\n{titulo}")
    for n, x in enumerate(itens, 1):
        print(f"  {n}. {rotulo(x)}")
    print("  0. Voltar")
    op = opcao(len(itens))
    return itens[op - 1] if op else None


def menu():
    try:
        temas, regs, avisos = carregar()
    except ValueError as e:
        print(f"Não foi possível iniciar: {e}. Verifique data/base_conhecimento.json."); return 1
    modelo = "B"
    print("=" * 60 + "\n CITIZEN ASSIST AI\n " + NAO_OFICIAL + "\n" + "=" * 60)
    while True:
        print(f"\nMENU\n  1. Escolher um tema\n  2. Fazer uma pergunta\n  3. Trocar modelo de resposta (atual: {modelo})"
              f"\n  4. Avisos da base ({len(avisos)})\n  0. Sair")
        op = opcao(4)
        if op == 0:
            print("Até logo!"); return 0
        if op == 1:
            tid = escolher("Temas:", list(temas), lambda t: f"{temas[t]['nome']} - {temas[t]['descricao']}")
            if tid:
                r = escolher(temas[tid]["nome"] + ":", [x for x in regs.values() if x["tema"] == tid],
                             lambda x: x["pergunta"] or x["subtema"])
                if r: mostrar(regs, modelo, r)
        elif op == 2:
            status, res = buscar(ler("\nDigite sua dúvida (sem dados pessoais): "), regs)
            if status == "ok":
                if len(res) > 1: print(f"({len(res)} orientações encontradas; mostrando a mais adequada.)")
                mostrar(regs, modelo, res[0])
            elif status == "ambigua":
                r = escolher("Sua pergunta pode ser sobre mais de um assunto. Qual?", res, lambda x: f"{x['subtema']}: {x['pergunta']}")
                if r: mostrar(regs, modelo, r)
            else:
                print("\n" + MENSAGENS[status])
                if status == "sem_correspondencia":
                    print("Temas disponíveis: " + "; ".join(t["nome"] for t in temas.values()))
        elif op == 3:
            modelo = "A" if modelo == "B" else "B"; print("Modelo:", MODELOS[modelo])
        elif op == 4:
            print("\n".join(avisos) or "Nenhum aviso.")


# ---------- 5. Testes e indicadores ----------
def testes(repeticoes=200):
    _, regs, _ = carregar()
    with open(TESTES, encoding="utf-8") as f:
        casos = json.load(f)
    linhas, tempos, acertos = [], [], 0
    pts = {"A": [], "B": []}
    for c in casos:
        ini = time.perf_counter()
        for _ in range(repeticoes):
            status, res = buscar(c["entrada"], regs)
        ms = (time.perf_counter() - ini) / repeticoes * 1000
        esp = c["esperado"]
        if esp == "SEM_RESPOSTA":   ok = status == "sem_correspondencia"
        elif esp == "ENTRADA_INVALIDA": ok = status in ("vazia", "invalida", "dados_pessoais")
        elif esp == "AMBIGUA":      ok = status == "ambigua"
        else:                       ok = status == "ok" and res[0]["id"] == esp
        obtido = res[0]["id"] if status == "ok" else status
        acertos += ok; tempos.append(ms)
        linhas.append([c["id"], c["tipo"], c["entrada"], esp, obtido, "ACERTO" if ok else "ERRO", f"{ms:.4f}"])
        if status == "ok":   # critérios objetivos: fonte, data, aviso não oficial, aviso de confirmação, rótulos
            for m in "AB":
                t = formatar(m, res[0])
                pts[m].append(sum([res[0]["referencia"] in t, "VERIFICADO EM" in t, NAO_OFICIAL in t,
                                   (not res[0]["requer_confirmacao"]) or "onfirme" in t, "ORIENTAÇÃO:" in t]))
    for l in linhas:
        print(f"{l[0]:4} {l[1]:13} {l[3]:17} {l[4]:20} {l[5]:7} {l[6]:>8} ms")
    print(f"\nTaxa de acerto: {acertos}/{len(casos)} = {acertos / len(casos) * 100:.1f}%")
    print(f"Tempo médio de consulta: {sum(tempos) / len(tempos):.4f} ms")
    for m in "AB":
        print(f"Modelo {m}: {sum(pts[m]) / len(pts[m]):.2f}/5 critérios atendidos")
    saida = os.path.join(RAIZ, "docs", "resultados_testes.csv")
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    with open(saida, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "tipo", "entrada", "esperado", "obtido", "resultado", "tempo_ms"])
        w.writerows(linhas)
    print("Resultados salvos em docs/resultados_testes.csv")


if __name__ == "__main__":
    if "--testes" in sys.argv:
        testes()
    else:
        sys.exit(menu())
