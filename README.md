# Citizen Assist AI

> Assistente digital de orientação cidadã (protótipo em Python, interface de texto) — Global Solution 2026.2 · FIAP

## 👥 Equipe

| Nome | RM |
|------|----|
| Ana Gabriela | rm571312 |
| Kaique | rm570533 |
| Miguel Antunes | rm573643 |
| Miguel Gonçalves | rm573793 |

**Vídeo de apresentação :** ``

---

## 1. Problema, público e temas

Cidadãos precisam de orientações confiáveis sobre documentos, serviços e direitos, mas as informações costumam estar espalhadas, mal organizadas e sujeitas a interpretações erradas. Isso torna a busca lenta e confusa.

O **Citizen Assist AI** organiza uma base de orientações verificadas, permite que a pessoa **escolha um tema no menu ou escreva uma pergunta**, localiza a orientação mais adequada, **cita a fonte** e **avisa quando não há resposta suficiente** na base.

**Público beneficiado:** qualquer cidadão com dúvidas simples do cotidiano, sobretudo quem tem pouca familiaridade com portais públicos.

**Temas abordados (4 temas, 21 registros):**

| Tema | Conteúdo |
|---|---|
| Documentação (`DOC-*`) | RG/CIN, CPF, certidões, título de eleitor e carteira de trabalho |
| Serviços públicos e benefícios (`SRV-*`) | INSS, Cadastro Único, Bolsa Família, SUS e seguro-desemprego |
| Direitos e proteção (`DIR-*`) | Consumidor, violência, assistência jurídica gratuita e juizados |
| Orientações comunitárias (`COM-*`) | Emergências, CRAS e Conselho Tutelar |

> ⚠️ **Protótipo educacional.** Não é canal oficial, não tem ligação com órgãos públicos e não substitui a consulta à fonte oficial.

---

## 2. Como executar

Requisitos: **Python 3.8+**. Não há dependências externas (apenas biblioteca padrão: `csv`, `json`, `os`, `re`, `sys`, `time`, `unicodedata`).

```bash
# Menu interativo
python src/sistema.py

# Bateria de testes (gera docs/resultados_testes.csv)
python src/sistema.py --testes
```

### Estrutura do repositório

```
.
├── README.md
├── src/
│   └── sistema.py                 # código-fonte (carga, busca, respostas, menu e testes)
├── data/
│   ├── base_conhecimento.json     # base de orientações verificadas
│   └── perguntas_teste.json       # 19 casos de teste
└── docs/
    ├── resultados_testes.csv      # gerado por --testes
    └── uso_ia.md                  # registro do uso de IA e validação crítica
```

> Ajuste a estrutura acima para coincidir com o modelo oficial da coordenação, caso haja diferenças.

---

## 3. Base de conhecimento

### Formato (`data/base_conhecimento.json`)

O arquivo possui dois blocos: `temas` (dicionário) e `registros` (lista).

```json
{
  "temas":     { "documentacao": { "nome": "Documentação", "descricao": "..." } },
  "registros": [ { "id": "DOC-003", "tema": "documentacao", "subtema": "CPF", "...": "..." } ]
}
```

| Campo | Obrigatório | Descrição |
|---|:---:|---|
| `id` | ✅ | Identificador único (ex.: `DOC-001`) |
| `tema` | ✅ | Chave que deve existir em `temas` |
| `palavras_chave` | ✅ | Lista não vazia de termos/frases usados na busca |
| `orientacao` | ✅ | Orientação resumida apresentada ao usuário |
| `referencia` | ✅ | URL da fonte consultada |
| `data_verificacao` | ✅ | Data em que a informação foi conferida na fonte |
| `subtema` | opcional | Nível intermediário da hierarquia (padrão: `"Geral"`) |
| `pergunta` | opcional | Pergunta-modelo exibida nos menus |
| `requer_confirmacao` | opcional | Se `true` (padrão), exibe aviso para confirmar requisitos atuais |
| `relacionados` | opcional | Lista de ids ligados a este registro (arestas do grafo) |

### Validação na carga (`carregar()`)

- Arquivo **ausente ou vazio** → mensagem clara e o programa não inicia.
- **JSON inválido** ou sem `temas`/`registros` → mensagem de formato esperado.
- Registro com **campos obrigatórios ausentes**, **tema inexistente**, **palavras-chave vazias** ou **id repetido** → é ignorado e listado em *Avisos da base* (opção 4 do menu).
- Registro sem data de verificação → aviso "ainda não conferido".
- Ligações em `relacionados` para ids inexistentes ou para o próprio registro são removidas.

### Como acrescentar ou corrigir orientações

Basta editar `data/base_conhecimento.json`. **Nenhuma regra do programa precisa ser alterada:** menus, busca e navegação são construídos a partir dos dados.

---

## 4. Estruturas de dados e organização dos temas

- **Dicionário** `temas` (id do tema → nome e descrição).
- **Dicionário** `regs` (id do registro → registro), com recuperação direta por identificador.
- **Listas** de palavras-chave, de resultados ordenados e de relacionados.
- **Conjuntos (`set`)** para comparar palavras da consulta com as palavras-chave.

### Hierarquia e grafo simples

Os assuntos seguem uma **hierarquia de três níveis**: `tema → subtema → registro`.

Além disso, o campo `relacionados` forma um **grafo dirigido simples** (lista de adjacência): cada registro é um nó e cada id em `relacionados` é uma aresta para um assunto de continuidade. Exemplo:

```
DOC-001 (RG/CIN) ──► DOC-002 (CIN digital)
        │        └──► DOC-003 (CPF)
        └───────────► DOC-005 (Certidões)

SRV-002 (CadÚnico) ──► SRV-003 (Bolsa Família) ──► COM-002 (CRAS)
```

Após cada resposta, o menu lista os assuntos relacionados (navegação entre 3 ou mais assuntos); o usuário pode seguir de um nó a outro até voltar ao menu com `0`.

---

## 5. Estratégia de busca

Busca por **palavras-chave com pontuação**, em quatro etapas (`tokens`, `pontuar`, `buscar`):

1. **Normalização:** minúsculas, remoção de acentos e pontuação, remoção de *stopwords* (artigos, preposições, "como", "quero", "preciso"...) e redução simples de plural (remove o `s` final).
2. **Pontuação** de cada registro em relação à consulta:
   - **+4** (mais 1 por palavra extra da frase) para cada **frase de palavra-chave inteira** encontrada na consulta (ex.: "carteira de trabalho");
   - **+2** por palavra da consulta presente nas palavras-chave;
   - **+1** por palavra que aparece apenas na pergunta-modelo ou no subtema.
3. **Corte mínimo:** registros com menos de `MIN_PONTOS = 3` pontos são descartados.
4. **Ordenação** por pontuação decrescente (desempate por id, o que torna o resultado determinístico). Retornam até 4 resultados: o primeiro é a melhor resposta e os demais são alternativas.

### Comportamento com várias correspondências

| Situação | Resultado |
|---|---|
| Um registro se destaca | `ok`: mostra o melhor e informa quantas orientações foram encontradas |
| Os dois primeiros ficam a ≤ `MARGEM = 1` ponto **e** têm subtemas diferentes | `ambigua`: o usuário escolhe entre até 4 opções |
| Nenhum registro atinge a pontuação mínima | `sem_correspondencia`: aviso de limitação, sem inventar resposta |

---

## 6. Regras de resposta e modelos de prompt/instrução

A resposta é gerada **exclusivamente a partir da base** (sem modelo de IA externo e sem API). As instruções de cada modelo estão documentadas no dicionário `MODELOS` do código.

### Modelo A — Direto

- **Papel:** guia breve.
- **Formato:** orientação + fonte (+ aviso de confirmação quando aplicável).
- **Regra:** só usar a base e citar a fonte.

```
<orientação>
Fonte: <URL>
Aviso: Confirme requisitos, prazos e valores atuais na fonte oficial antes de agir.
```

### Modelo B — Estruturado (padrão)

- **Papel:** assistente **não oficial**.
- **Formato:** `ASSUNTO / ORIENTAÇÃO / FONTE / VERIFICADO EM / AVISO / NOTA`.
- **Regras:** só usar a base, citar fonte **e data**, avisar que não é oficial e destacar a necessidade de confirmação.

```
ASSUNTO: CPF (DOC-003)
ORIENTAÇÃO: <texto>
FONTE: <URL>
VERIFICADO EM: <data ou "pendente de conferência">
AVISO: Confirme requisitos, prazos e valores atuais na fonte oficial antes de agir.
NOTA: Protótipo educacional: não é atendimento oficial nem tem ligação com órgãos públicos.
```

O usuário alterna entre os modelos pela opção 3 do menu.

### Comparação dos modelos

Os dois modelos foram avaliados nas consultas que retornaram resposta (`status = ok`), com **5 critérios objetivos**: (1) cita a fonte, (2) informa a data de verificação, (3) avisa que não é oficial, (4) destaca confirmação quando exigida, (5) usa rótulos de seção.

| Modelo | Critérios atendidos (média) |
|---|:---:|
| A — Direto | **2,00 / 5** |
| B — Estruturado | **5,00 / 5** |

**Conclusão:** o **Modelo B** é mais claro e consistente, pois sempre expõe fonte, data, natureza não oficial e aviso de confirmação, o que atende melhor ao requisito de transparência. O Modelo A é mais curto e pode servir para consultas rápidas. *Observação:* os critérios favorecem naturalmente o formato mais completo; a comparação mede consistência e transparência, não preferência de leitura.

### Tratamento de limitações

| Situação | Mensagem do sistema |
|---|---|
| Entrada vazia | Pede que a pessoa escreva a dúvida ou escolha um tema |
| Entrada inválida (só números/símbolos ou mais de 300 caracteres) | Pede palavras simples sobre o assunto |
| Dados pessoais (padrão de CPF) | Recusa a consulta e orienta a reescrever sem dados pessoais |
| Sem correspondência | Informa que não há base confiável, não responde por conta própria, lista os temas disponíveis e sugere procurar o órgão responsável |
| Ambiguidade | Pergunta qual assunto a pessoa quis dizer |
| Opção de menu vazia ou inexistente | Mensagem específica e novo pedido de escolha |

---

## 7. Exemplos de uso

**Pergunta direta**

```
> Como emitir a segunda via do CPF?
ASSUNTO: CPF (DOC-003)
ORIENTAÇÃO: ...
FONTE: https://www.gov.br/pt-br/servicos/obter-cartao-de-cpf
VERIFICADO EM: 2026-11-14
NOTA: Protótipo educacional: não é atendimento oficial nem tem ligação com órgãos públicos.

Assuntos relacionados:
  1. CPF: Como me inscrever no CPF pela primeira vez?
  2. Identidade (RG/CIN): Como solicitar a primeira via da Carteira de Identidade Nacional (CIN)?
  0. Voltar ao menu
```

**Reformulação:** `fui demitido, como peço o seguro-desemprego?` → `SRV-005` (fonte: gov.br/trabalho-e-emprego).

**Consulta ambígua:** `segunda via` → o sistema pergunta se é sobre CPF, certidão, etc.

**Fora do tema:** `Qual a previsão do tempo para amanhã?` → "Não encontrei informação confiável sobre isso na base, então não vou arriscar uma resposta..." + lista de temas.

**Dados pessoais:** `meu cpf é 123.456.789-09, e agora?` → "Parece um número de documento. Por privacidade, não informe dados pessoais; reescreva sem eles."

**Entrada vazia:** → "Você não digitou nada. Escreva sua dúvida ou escolha um tema no menu."

---

## 8. Plano de testes, indicadores e resultados

### Plano

`data/perguntas_teste.json` contém **19 casos** (mínimo exigido: 12):

| Tipo | Qtde | Objetivo |
|---|:---:|---|
| Direta | 7 | Pergunta clara com registro esperado |
| Reformulação | 5 | Linguagem informal ou indireta |
| Fora do tema | 2 | Deve resultar em "sem resposta" |
| Limite | 5 | Entrada vazia, ambígua, só símbolos, dado pessoal e dúvida sem base |

Cada caso informa a resposta esperada (um id, `SEM_RESPOSTA`, `ENTRADA_INVALIDA` ou `AMBIGUA`). O tempo é medido com `time.perf_counter()` como a **média de 200 repetições** por consulta. Os resultados completos ficam em `docs/resultados_testes.csv`.

### Resultados obtidos

| ID | Tipo | Esperado | Obtido | Resultado | Tempo (ms) |
|---|---|---|---|:---:|---:|
| T01 | direta | DOC-001 | DOC-001 | ✅ | 0,5428 |
| T02 | reformulação | DOC-001 | DOC-001 | ✅ | 0,5353 |
| T03 | direta | DOC-002 | DOC-002 | ✅ | 0,5405 |
| T04 | direta | DOC-003 | DOC-003 | ✅ | 0,5429 |
| T05 | reformulação | DOC-003 | DOC-003 | ✅ | 0,5472 |
| T06 | direta | DOC-005 | DOC-005 | ✅ | 0,5463 |
| T07 | reformulação | DOC-007 | DOC-007 | ✅ | 0,5404 |
| T08 | direta | SRV-002 | SRV-002 | ✅ | 0,5443 |
| T09 | reformulação | SRV-005 | SRV-005 | ✅ | 0,5353 |
| T10 | direta | DIR-001 | DIR-001 | ✅ | 0,5408 |
| T11 | reformulação | DIR-003 | DIR-003 | ✅ | 0,5415 |
| T12 | direta | COM-001 | COM-001 | ✅ | 0,5300 |
| T13 | fora do tema | SEM_RESPOSTA | sem_correspondencia | ✅ | 0,7510 |
| T14 | fora do tema | SEM_RESPOSTA | sem_correspondencia | ✅ | 0,5805 |
| T15 | limite | ENTRADA_INVALIDA | vazia | ✅ | 0,0001 |
| T16 | limite | AMBIGUA | ambigua | ✅ | 0,5259 |
| T17 | limite | ENTRADA_INVALIDA | invalida | ✅ | 0,5234 |
| T18 | limite | ENTRADA_INVALIDA | dados_pessoais | ✅ | 0,0006 |
| T19 | limite | SEM_RESPOSTA | sem_correspondencia | ✅ | 0,5347 |

### Indicadores

| Indicador | Valor |
|---|---|
| Taxa de acerto | **19/19 = 100,0 %** |
| Tempo médio de consulta | **0,4949 ms** |
| Modelo A (critérios atendidos) | 2,00 / 5 |
| Modelo B (critérios atendidos) | 5,00 / 5 |

### Teste de facilidade de uso

> **Preencher com os dados reais do teste (mínimo: 1 usuário ou roteiro de tarefas).** Sugestão de roteiro:

| Tarefa | Concluída? | Tempo | Dificuldades observadas |
|---|:---:|---|---|
| 1. Encontrar como tirar o CPF pelo menu de temas | `<sim/não>` | `<s>` | `<...>` |
| 2. Perguntar em texto como pedir seguro-desemprego | `<sim/não>` | `<s>` | `<...>` |
| 3. Navegar até um assunto relacionado | `<sim/não>` | `<s>` | `<...>` |
| 4. Digitar uma pergunta fora do tema e entender a resposta | `<sim/não>` | `<s>` | `<...>` |

Perfil do usuário de teste: `<idade/familiaridade com tecnologia>` · Nota de facilidade (1 a 5): `<n>` · Comentários: `<...>`

### Interpretação

- A taxa de 100 % indica que a busca por palavras-chave com pontuação atende bem às perguntas previstas, inclusive reformulações informais, e que as limitações (vazio, símbolos, dado pessoal, ambiguidade, fora do tema) são tratadas corretamente.
- O tempo médio inferior a 1 ms mostra que o custo computacional da busca é desprezível para uma base desse tamanho (21 registros). O tempo real percebido pelo usuário é dominado por digitar e ler.
- O Modelo B supera o Modelo A em transparência (fonte, data, aviso e natureza não oficial).

### Limitações da avaliação

- Os casos de teste foram escritos pela própria equipe, que conhece a base. Isso tende a **superestimar a taxa de acerto**; usuários reais escreveriam de formas imprevistas.
- Amostra pequena (19 casos) e sem variações de digitação (erros ortográficos, gírias).
- O tempo mede só a busca em memória, não a experiência completa de uso.
- A comparação entre modelos usa critérios objetivos de formato e **não mede a compreensão** do usuário.
- A avaliação **não verifica se o conteúdo das orientações continua atualizado** na fonte oficial.

---

## 9. Cuidados com clareza, acessibilidade, privacidade e informação não oficial

- **Não oficial:** o banner inicial e a nota nas respostas do Modelo B deixam claro que é um protótipo educacional, sem vínculo com órgãos públicos.
- **Fonte e data:** toda orientação exibe a referência consultada e a data de verificação (ou "pendente de conferência").
- **Aviso de confirmação:** orientações com `requer_confirmacao = true` pedem conferência de requisitos, prazos e valores na fonte oficial.
- **Privacidade:** o sistema não pede, não armazena e não registra dados pessoais; se detecta padrão de CPF, recusa a consulta e orienta a reescrever sem ele.
- **Sem invenção:** quando não há base suficiente, informa o limite, sugere alternativas e não gera resposta própria.
- **Clareza e acessibilidade:** interface de texto, linguagem simples, menus numerados, mensagens de erro compreensíveis e entrada que aceita acentos e maiúsculas/minúsculas.

---

## 10. Uso de inteligência artificial

O uso de IA no desenvolvimento (apoio à elaboração de prompts, revisão de textos e planejamento de testes) e a validação crítica realizada estão registrados em [`docs/uso_ia.md`](docs/uso_ia.md). O protótipo **não** depende de nenhum modelo externo em tempo de execução: todas as respostas vêm da base verificada.

---

## 11. Conclusões, limitações e melhorias

### Conclusões

O protótipo cumpre o fluxo completo: pergunta ou menu → busca → orientação com fonte, data e avisos → navegação por assuntos relacionados, com tratamento de erros e testes documentados.

### Limitações

- Base pequena (21 registros) e restrita a 4 temas.
- A busca é lexical: não entende sinônimos que não estejam nas palavras-chave nem lida com erros de digitação.
- As informações ficam desatualizadas se não forem reverificadas.
- Interface apenas de texto.

### Melhorias possíveis

1. **Tolerância a erros de digitação e sinônimos**, com distância de edição (Levenshtein) ou lista de sinônimos, aumentando a taxa de acerto com usuários reais.
2. **Ampliar o teste de usabilidade e os casos de teste** com pessoas externas à equipe e perguntas coletadas de forma anônima.
3. **Rotina de revalidação** que sinalize registros com `data_verificacao` antiga ou vazia.
4. Interface web ou gráfica com maior acessibilidade (contraste, leitor de tela).
5. Ampliar a base com novos temas (educação, moradia, mobilidade).

---

*Protótipo educacional desenvolvido para a Global Solution 2026.2 — FIAP. Não é um canal oficial.*
