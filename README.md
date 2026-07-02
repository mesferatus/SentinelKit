<h1 align="center">
  ☾ SentinelKit ☽
</h1>

<p align="center">
  Plataforma desktop para estudos e demonstrações de segurança defensiva em ambientes autorizados.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Desktop-Electron-1f2a44?style=flat-square&logo=electron"/>
  <img src="https://img.shields.io/badge/Front--end-Vue-183150?style=flat-square&logo=vuedotjs"/>
  <img src="https://img.shields.io/badge/API-FastAPI-18a6b4?style=flat-square&logo=fastapi"/>
  <img src="https://img.shields.io/badge/Security-Responsible_Use-f26167?style=flat-square"/>
</p>

---

## ✦ Sumário

- Sobre o Projeto
- Para que Serve
- Funcionalidades
- Como Demonstrar
- Tecnologias
- Segurança e Uso Responsável
- Executável Windows
- Limitações

---

## ✦ Sobre o Projeto

O SentinelKit é um aplicativo desktop voltado para apoiar estudos, demonstrações e práticas de segurança defensiva.  
A proposta é reunir, em uma interface simples, recursos básicos de reconhecimento, auditoria web, análise de logs e rastreabilidade de ações.

O projeto foi pensado para uso local e educacional, sempre com foco em alvos próprios, laboratoriais ou expressamente autorizados.

---

## ✦ Para que Serve

O SentinelKit ajuda a responder perguntas simples de segurança, como:

- Quais portas estão expostas em um alvo autorizado?
- Uma aplicação web possui configurações básicas de segurança?
- Existem padrões suspeitos em logs analisados?
- Quais ações foram executadas dentro da plataforma?

Ele não tem a intenção de substituir ferramentas profissionais de pentest, SIEM ou gestão de vulnerabilidades.  
O foco é demonstrar conceitos de forma organizada, visual e responsável.

---

## ✦ Funcionalidades

| Área | Descrição |
|---|---|
| Dashboard | Visão inicial com resumo das análises e atividades recentes |
| Alvos autorizados | Cadastro de ambientes que podem ser analisados |
| Recon | Verificação básica de portas em alvos permitidos |
| Web Audit | Checagem de configurações web, como headers, cookies e TLS |
| SIEM | Análise simples de logs para identificar padrões suspeitos |
| Logs de auditoria | Registro de ações realizadas na plataforma |
| Perfil | Edição dos dados do usuário dentro do app |

---

## ✦ Como Demonstrar

Uma demonstração curta pode seguir este roteiro:

1. Abrir o aplicativo desktop.
2. Acessar a plataforma com uma conta local criada no próprio app.
3. Cadastrar um alvo autorizado para teste.
4. Executar um Recon para visualizar portas analisadas.
5. Rodar um Web Audit em uma URL autorizada.
6. Enviar um arquivo de log de exemplo no SIEM.
7. Mostrar os logs de auditoria gerados pela própria plataforma.

Durante a apresentação, vale reforçar que o SentinelKit não realiza ataques.  
Ele organiza verificações defensivas e só deve ser usado com autorização.

---

## ✦ Tecnologias

### Desktop e Interface

| Tecnologia | Uso |
|---|---|
| Electron | Empacotamento como aplicativo desktop Windows |
| Vue 3 | Construção da interface |
| Vite | Build do front-end |
| Pinia | Controle de estado |
| Axios | Comunicação com a API local |

### API e Segurança

| Tecnologia | Uso |
|---|---|
| FastAPI | API local da aplicação |
| SQLAlchemy | Camada de persistência |
| PyInstaller | Empacotamento da API para o desktop |
| Pytest | Testes automatizados da API |
| Vitest | Testes automatizados do front-end |

---

## ✦ Segurança e Uso Responsável

O SentinelKit foi construído com uma premissa simples: segurança precisa de autorização.

Boas práticas adotadas no projeto:

- uso voltado a ambientes próprios, laboratoriais ou autorizados;
- cadastro explícito de alvo antes das verificações;
- separação entre interface desktop e API local;
- cuidado para não expor dados sensíveis no repositório;
- registro de ações relevantes em logs de auditoria;
- foco em demonstração defensiva, não exploração ofensiva.

> Use somente em sistemas que você possui ou tem permissão clara para testar.  
> Testar sistemas de terceiros sem autorização pode ser ilegal.

---

## ✦ Executável Windows

O projeto gera um aplicativo `.exe` para Windows.

Arquivos finais de build podem ser gerados localmente na pasta `release/`.  
Por segurança e tamanho, a recomendação é versionar apenas o código-fonte e manter fora do GitHub qualquer artefato local ou material sensível.

### Assinatura digital

O executável não possui assinatura digital.  
Isso significa que o Windows pode mostrar um aviso do SmartScreen ou informar que o publicador é desconhecido.

Para uma publicação profissional, o ideal seria assinar o `.exe` com um certificado de code signing.  
Para apresentação acadêmica ou demonstração local, essa assinatura não é obrigatória.

---

## ✦ Revisão Visual

Antes de publicar ou apresentar, é recomendado abrir o aplicativo no tamanho real da tela usada na demonstração e revisar:

- alinhamento das margens entre abas;
- cards sem corte no rodapé;
- telas sem necessidade de rolagem;
- legibilidade dos textos;
- consistência da identidade visual.

---

## ✦ Limitações

- O Recon é básico e deve ser usado apenas em alvos autorizados.
- O Web Audit verifica um conjunto limitado de itens de configuração.
- A análise SIEM é demonstrativa e não substitui uma solução corporativa.
- A versão desktop foi pensada para uso local.
- O `.exe` pode exibir aviso de segurança por não estar assinado digitalmente.

---

<p align="center">
  Feito para estudar segurança com cuidado, responsabilidade e um pouco de fofura.
</p>
