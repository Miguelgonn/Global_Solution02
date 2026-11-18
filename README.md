# Global Solution Citizen Assist AI

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

Informações sobre documentos, serviços e direitos costumam estar espalhadas e confusas. O Citizen Assist AI organiza orientações verificadas, permite escolher um tema ou digitar uma pergunta, mostra a **fonte** e **avisa quando não há resposta confiável**.

**Público:** cidadãos com dúvidas simples do cotidiano.

**Temas (4 temas, 21 registros):** Documentação (RG/CIN, CPF, certidões, título, carteira de trabalho) · Serviços e benefícios (INSS, CadÚnico, Bolsa Família, SUS, seguro-desemprego) · Direitos e proteção (consumidor, violência, defensoria, juizados) · Orientações comunitárias (emergências, CRAS, Conselho Tutelar).

## 2. Como executar

Python 3.8+, sem dependências externas.

```bash
python src/sistema.py            # menu interativo
python src/sistema.py --testes   # gera docs/resultados_testes.csv
```

```
src/sistema.py                 código
data/base_conhecimento.json    base de orientações
data/perguntas_teste.json      19 casos de teste
docs/resultados_testes.csv     resultados dos testes
docs/uso_ia.md                 uso de IA
```

## 3. Base de conhecimento, estruturas e busca

**Arquivo:** `data/base_conhecimento.json`, com `temas` (dicionário) e `registros` (lista).

| Campo | Obrigatório | Uso |
|---|:---:|---|
| `id`, `tema`, `palavras_chave`, `orientacao`, `referencia`, `data_verificacao` | ✅ | Dados essenciais de cada orientação |
| `subtema`, `pergunta`, `requer_confirmacao`, `relacionados` | opcional | Menus, aviso de confirmação e navegação |

**Origem:** cada orientação é um resumo de uma fonte pública oficial (gov.br, Meu INSS, TSE, Consumidor.gov.br, DPU, leis no Planalto), registrada em `referencia`, com a data da conferência em `data_verificacao`.

**Validação na carga:** arquivo ausente, vazio ou com JSON inválido impede o início com mensagem clara. Registros com campos ausentes, tema inexistente ou id repetido são ignorados e listados em "Avisos da base" (opção 4 do menu).

**Manutenção:** para acrescentar ou corrigir orientações basta editar o JSON, sem mexer no código.

**Estruturas:** dicionários (temas e registros por id), listas (palavras-chave e resultados) e conjuntos (comparação de palavras).

**Organização dos assuntos:** hierarquia `tema → subtema → registro` e um **grafo simples** em `relacionados` (lista de adjacência). Dois assuntos são ligados quando um é o passo seguinte do outro (ex.: RG ↔ CIN digital; seguro-desemprego ↔ Carteira de Trabalho). Após cada resposta, o menu oferece esses assuntos para continuar a consulta.

**Estratégia de busca (palavras-chave com pontuação):**

1. Normaliza o texto (minúsculas, sem acentos, sem *stopwords*, plural simplificado).
2. Pontua cada registro: **+4** por frase de palavra-chave inteira (+1 por palavra extra), **+2** por palavra em palavra-chave, **+1** por palavra na pergunta/subtema.
3. Descarta registros abaixo de 3 pontos e ordena do maior para o menor (desempate por id).

**Várias correspondências:** mostra o melhor resultado. Se os dois primeiros ficam a até 1 ponto e são de subtemas diferentes, a consulta é **ambígua** e o usuário escolhe entre até 4 opções. Se nenhum atinge o mínimo, informa que não há resposta.

## 4. Regras de resposta, modelos de prompt e limitações

A resposta usa **somente a base**, sem IA externa nem API.

| Modelo | Papel | Formato | Regras |
|---|---|---|---|
| **A – Direto** | Guia breve | Orientação + fonte (+ aviso) | Usar só a base e citar a fonte |
| **B – Estruturado** (padrão) | Assistente **não oficial** | ASSUNTO / ORIENTAÇÃO / FONTE / VERIFICADO EM / AVISO / NOTA | Usar só a base, citar fonte e data, avisar que não é oficial, destacar confirmação |

**Tratamento de limitações:**

| Situação | Comportamento |
|---|---|
| Entrada vazia | Pede para digitar a dúvida ou escolher um tema |
| Entrada inválida (só números/símbolos, mais de 300 caracteres) | Pede palavras simples sobre o assunto |
| Dado pessoal (padrão de CPF) | Recusa e orienta a reescrever sem dados pessoais |
| Sem correspondência | Avisa que não há base confiável, não inventa resposta, lista os temas disponíveis |
| Consulta ambígua | Pergunta qual assunto a pessoa quis dizer |
| Opção de menu inexistente | Mensagem de erro e nova escolha |

## 5. Exemplos

```
> Como emitir a segunda via do CPF?
ASSUNTO: CPF (DOC-003)
ORIENTAÇÃO: O comprovante de inscrição no CPF pode ser emitido gratuitamente no site da Receita Federal, no portal/app gov.br ou no e-CAC. [...]
FONTE: https://www.gov.br/pt-br/servicos/obter-cartao-de-cpf
VERIFICADO EM: 2026-11-14
NOTA: Protótipo educacional: não é atendimento oficial nem tem ligação com órgãos públicos.

> segunda via
Sua pergunta pode ser sobre mais de um assunto. Qual?
  1. CPF: Como obter a segunda via ou comprovante do CPF?
  2. Certidões: Como pedir a segunda via da certidão de nascimento ou casamento?

> Qual a previsão do tempo para amanhã?
Não encontrei informação confiável sobre isso na base, então não vou arriscar uma resposta. [...]

> meu cpf é 123.456.789-09, e agora?
Parece um número de documento. Por privacidade, não informe dados pessoais; reescreva sem eles.
```

## 6. Testes e indicadores

**Plano:** 19 casos em `data/perguntas_teste.json` (7 diretas, 5 reformulações, 2 fora do tema, 5 de limite), cada um com a resposta esperada. O tempo é a média de 200 repetições por consulta. Resultados completos em `docs/resultados_testes.csv`.

| Indicador | Resultado |
|---|---|
| Taxa de acerto | **19/19 = 100 %** |
| Tempo médio de consulta | **0,4949 ms** |
| Modelo A / Modelo B | 2,00/5 · 5,00/5 |

**Teste de facilidade de uso** (`<preencher com o teste real>`):

| Tarefa | Concluída? | Tempo | Dificuldades |
|---|:---:|---|---|
| Achar o CPF pelo menu de temas | `<sim/não>` | `<s>` | `<...>` |
| Perguntar sobre seguro-desemprego em texto | `<sim/não>` | `<s>` | `<...>` |
| Navegar até um assunto relacionado | `<sim/não>` | `<s>` | `<...>` |



## 7. Cuidados

- **Clareza e acessibilidade:** linguagem simples, menus numerados e mensagens de erro compreensíveis.
- **Privacidade:** não pede nem armazena dados pessoais; recusa consultas com padrão de CPF.
- **Informação não oficial:** o banner inicial e a nota nas respostas deixam claro que não é atendimento oficial; toda resposta traz fonte e data, e orientações sensíveis a mudanças pedem confirmação na fonte oficial.

## 8. Uso de IA

### Uso de Inteligência Artificial

Durante o desenvolvimento deste projeto, utilizamos ferramentas de Inteligência Artificial como apoio na organização, estruturação e otimização do código-fonte.

Após a utilização da IA, realizamos testes para verificar o funcionamento do código e avaliar se as soluções propostas atendiam aos requisitos do projeto. Com base nos resultados obtidos, analisamos e adaptamos os trechos necessários, realizando alterações conforme identificamos ser adequado.

Dessa forma, a IA foi utilizada como uma ferramenta de apoio ao desenvolvimento, enquanto a validação, os testes e as decisões sobre as adaptações foram realizados pela equipe.mos os menus e entradas disponíveis.

Foi usada uma ferramenta de IA (Claude, da Anthropic) como apoio à revisão do projeto .


## 9. Conclusões, limitações e melhorias

**Conclusão:** o protótipo cumpre o fluxo completo (pergunta ou menu → busca → orientação com fonte, data e aviso → navegação por assuntos relacionados), com tratamento de erros e testes documentados.

**Limitações:** base pequena (21 registros, 4 temas); busca lexical, sem sinônimos nem tolerância a erros de digitação; informações podem ficar desatualizadas; interface só de texto.

**Melhorias:** (1) tolerar erros de digitação e sinônimos (distância de edição ou lista de sinônimos); (2) ampliar os testes com usuários externos e perguntas reais; (3) rotina que sinalize registros com data de verificação antiga; (4) interface web acessível.
