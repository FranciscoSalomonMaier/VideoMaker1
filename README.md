# VideoMaker

VideoMaker é um projeto para automatizar a criação de vídeos para YouTube a partir de assuntos de tecnologia que estejam ganhando relevância. O sistema deve apoiar todo o processo, da descoberta de pautas à preparação do vídeo final, mantendo uma etapa obrigatória de revisão humana antes da publicação.

## Escopo inicial

O primeiro formato previsto pelo produto tem estas características:

- conteúdo sobre tecnologia;
- vídeos com duração de 5 a 8 minutos;
- produção em português;
- narração gerada por inteligência artificial;
- formato sem apresentador em cena (*faceless*);
- revisão e aprovação manual antes da publicação.

## Visão geral da solução

A arquitetura abaixo é uma recomendação inicial. Ela organiza o processo como um pipeline, permitindo executar, testar e substituir cada etapa de forma independente.

1. Descobrir assuntos em crescimento.
2. Avaliar e selecionar uma pauta.
3. Pesquisar fontes e reunir fatos.
4. Gerar e revisar o roteiro.
5. Produzir a narração.
6. Planejar e obter os recursos visuais.
7. Montar o vídeo.
8. Validar o resultado e solicitar aprovação humana.
9. Preparar ou realizar a publicação após a aprovação.

## Módulos principais

### Descoberta de tendências

Coleta sinais de fontes como Google Trends, notícias, feeds, redes sociais e dados do YouTube. Normaliza os resultados e identifica temas de tecnologia que estejam crescendo, evitando depender apenas de volume absoluto.

### Seleção e priorização de pautas

Pontua os temas encontrados considerando crescimento, atualidade, aderência ao canal, disponibilidade de fontes e potencial para um vídeo de 5 a 8 minutos. A pauta escolhida deve guardar a justificativa e os sinais que levaram à seleção.

### Pesquisa e referências

Reúne fontes confiáveis, extrai os fatos relevantes e registra links, datas e evidências. Esse material serve de base para o roteiro e reduz o risco de informações inventadas ou desatualizadas.

### Geração de roteiro

Transforma a pesquisa em um roteiro em português, com abertura, contexto, desenvolvimento, conclusão e chamada para ação. Também estima o tempo de narração e ajusta o texto à duração-alvo.

### Narração

Converte o roteiro aprovado em áudio por meio de um serviço de texto para fala. O módulo deve controlar voz, ritmo, pronúncias e pausas, além de gerar ou expor as marcações de tempo necessárias para a edição.

### Planejamento e aquisição visual

Divide o roteiro em cenas e associa cada trecho a imagens, vídeos de apoio, capturas, gráficos, títulos ou animações. Também registra origem e licença dos recursos para uso seguro na publicação.

### Composição e renderização

Sincroniza narração, cenas, legendas, trilha e efeitos; aplica o padrão visual do canal; e renderiza o arquivo final no formato esperado pelo YouTube.

### Controle de qualidade e revisão

Executa verificações automáticas de duração, resolução, áudio, legendas, arquivos ausentes e consistência do roteiro. Em seguida, disponibiliza uma prévia para revisão humana, com opções de aprovar, rejeitar ou solicitar ajustes.

### Publicação

Prepara título, descrição, referências, tags, miniatura e demais metadados. O envio ou agendamento no YouTube só pode acontecer depois de uma aprovação manual explícita.

### Orquestração e persistência

Coordena o estado de cada produção, as tentativas, os artefatos gerados e os erros. Cada vídeo deve ser rastreável desde a tendência original até o arquivo publicado.

## Stack recomendada

Como ainda não há uma stack definida no documento de produto, esta é uma proposta inicial voltada à automação e ao processamento de mídia:

- **Python 3.12+** para o pipeline, integrações, pesquisa e processamento de dados;
- **FastAPI** para expor operações e integrações por API;
- **Pydantic** para validar contratos entre as etapas;
- **PostgreSQL** para pautas, fontes, roteiros, revisões e estados do fluxo;
- **Redis e Celery** para filas, tarefas demoradas e novas tentativas;
- **FFmpeg** como base para composição, tratamento de áudio e renderização;
- **Remotion ou MoviePy** para definir a edição programática — Remotion quando layouts e animações forem mais importantes, MoviePy para uma primeira versão centrada em Python;
- **armazenamento compatível com S3** para áudio, imagens, clipes, prévias e vídeos finais;
- **um provedor de LLM** para classificação, síntese da pesquisa e criação assistida do roteiro;
- **um provedor de TTS** com suporte de qualidade ao português brasileiro;
- **YouTube Data API** para metadados, upload e agendamento, sempre após aprovação;
- **Docker Compose** para padronizar o ambiente local e os serviços de apoio;
- **pytest, Ruff e mypy** para testes, qualidade e análise estática.

A interface de revisão pode começar simples, usando páginas servidas pela própria API, e evoluir para um front-end dedicado em React/Next.js quando o fluxo estiver validado.

## Fluxo completo de geração de um vídeo

### 1. Coleta

Uma execução agendada consulta as fontes configuradas e cria candidatos de pauta com métricas, data de coleta e origem.

### 2. Ranqueamento

Os candidatos são deduplicados, classificados e filtrados por tecnologia, idioma, atualidade e adequação ao canal. O sistema seleciona automaticamente uma pauta ou apresenta uma lista curta para decisão humana.

### 3. Pesquisa

Para a pauta selecionada, o sistema coleta fontes, organiza fatos e contrapontos e produz um dossiê rastreável. Informações sem fonte suficiente devem ser descartadas ou sinalizadas.

### 4. Roteiro

O dossiê alimenta a geração do roteiro. Uma estimativa baseada na quantidade de palavras verifica se a narração ficará entre 5 e 8 minutos. O texto passa por checagens de clareza, repetição, tom e correspondência com as fontes.

### 5. Plano de cenas

O roteiro é dividido em blocos com duração estimada. Cada bloco recebe instruções visuais, texto na tela e indicação do recurso necessário, formando uma lista de cenas.

### 6. Áudio

O roteiro é convertido em narração. O resultado passa por normalização de volume e validação de duração. Marcações temporais da fala são preservadas para sincronizar cenas e legendas.

### 7. Recursos visuais

O sistema busca, gera ou captura os recursos previstos no plano de cenas, registra suas licenças e cria versões no tamanho e formato necessários. Recursos ausentes bloqueiam a renderização ou usam um substituto previamente aprovado.

### 8. Montagem

O compositor combina narração, visuais, títulos, transições, legendas e trilha. A mixagem mantém a voz inteligível, e o projeto gera primeiro uma prévia de menor custo para revisão.

### 9. Validação automática

A prévia é conferida quanto a duração, resolução, proporção, sincronização básica, níveis de áudio, presença de legendas e integridade dos artefatos. Falhas retornam à etapa responsável.

### 10. Revisão manual

Uma pessoa assiste à prévia e confere fatos, linguagem, pronúncia, ritmo, recursos visuais e possíveis problemas de direitos autorais. Ela pode aprovar ou solicitar alterações; cada solicitação retorna ao módulo correspondente e gera uma nova versão.

### 11. Renderização final

Depois da aprovação, o sistema produz o vídeo em alta qualidade e gera os artefatos complementares, como miniatura, título, descrição, capítulos, créditos e tags.

### 12. Publicação

Com uma aprovação final explícita, o vídeo e seus metadados podem ser enviados ou agendados no YouTube. O identificador da publicação e o status ficam registrados para auditoria.

## Estados sugeridos

Uma produção pode avançar pelos estados `descoberta`, `pauta_selecionada`, `pesquisa`, `roteiro`, `produção`, `prévia`, `em_revisão`, `ajustes_solicitados`, `aprovado`, `renderizado`, `agendado`, `publicado` ou `falhou`.

Os artefatos devem ser versionados. Uma alteração no roteiro, na voz ou em uma cena não deve apagar a versão anteriormente revisada.

## Princípios do projeto

- nenhuma publicação automática sem aprovação humana;
- fatos importantes vinculados às respectivas fontes;
- etapas idempotentes e retomáveis após falhas;
- rastreabilidade de entradas, decisões, versões e artefatos;
- fornecedores externos isolados por interfaces substituíveis;
- respeito a licenças, direitos autorais e políticas do YouTube;
- segredos e credenciais fora do código-fonte.

## Status

O projeto está na fase de definição. Este README descreve a arquitetura recomendada a partir dos requisitos atuais; nenhuma implementação é estabelecida por ele e as escolhas de fornecedores ainda precisam ser validadas em uma prova de conceito.
