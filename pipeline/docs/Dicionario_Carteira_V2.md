Conceitos Importantes:



A tabela se refere a uma carteira de clientes de um certo Polo Franquia, nesse caso específico o Polo de Parnaíba, da empresa Stone.



A Stone é uma empresa de Pagamentos, e também possui uma conta especializada em gestão de banking e crédito. 



Abaixo, temos a tabela de cadastros de clientes até aquele mês especifico (Primeira coluna) daquele Polo, com todos os outros meses anteriores empilhados abaixo. Dessa forma, cada cliente ou cadastro tem uma situação específica para aquele mês. 



A tabela posssui dados cujo dicionário abaixo descreverá com a maior precisão possível. 



É importante ressaltar que vários desses dados não são necessários para as analises que iremos fazer, possuindo missing values para certos meses, ou mesmo conceitos confusos ou desconhecidos. 



Outro ponto importante: ao longo dos meses o número de variáveis foi crescendo, até chegar ao maior número de colunas no mês mais recente.







Dicionário:



Atenção: não irei especificar quando o cabeçalho for redundante, já explicado anteriormente, ou quando o nome da coluna for autoexplicativo.



Data\_referencia: mês que possui os dados de todos os clientes credenciados até aquele mês. Perceba que o número de linhas dessa base somente cresce mês a mês.



Stonecode: código único do cliente. As vezes temos vários stonecodes em uma mesma linha;



Documento: CNPJ ou CPF do cliente. Note que o cliente pode ter apenas um documento, porém pode ter mais de um Stonecode, pois cada Stonecode se refere a um tipo de cadastro, se utiliza Canal\_Venda Link ABC, WhatsappPay, geralmente o cliente tem um Stonecode específico para cada cadastro)



Tipo\_documento: se o cadastro foi MEI, CNPJ ou CPF



Nome\_fantasia: Nome do cliente;



Status: especifica se o cadastro foi aprovado, reprovado, em análise, etc. Mesmo que o cliente tenha o cadastro rejeitado, fica registrado uma linha com essa informação.



Polo\_endereco: desconsiderar. variável de baixa cardinalidade;



Distrito\_franquia: desconsiderar. variável de baixa cardinalidade;



Regional\_franquia: desconsiderar. variável de baixa cardinalidade;



Cidade: cidade do cadastro do cliente; um polo possui várias cidades, e em alguns, parte de uma cidade;



UF: estado do cadastro do cliente; um polo pode atender cidades de mais de um estado;



Tipo\_endereco: endereço de entrega da maquina, ou endereço de cadastro; dependendo do mês analisado, o tipo de endereço muda.



Canal\_encarteiramento: desconsiderar;



Subcanal\_encarteiramento: desconsiderar;



Grupo\_1\_encarteiramento: desconsiderar;



Grupo\_2\_encarteiramento: desconsiderar



Grupo\_3\_encarteiramento: desconsiderar



Data\_credenciamento: data do cadastro do cliente, que difere da data de ativação; em geral falaremos mais da data de ativação, mais especificamente da primeira ativação. 



Vendedor: quem foi o vendedor que atuou; se tiver @querostone no email, significa que é um vendedor de operação de Polo Franquia. Existem Polos próprios, com vendedores @stone, e polos franquia, com vendedores @querostone. As vezes, no histórico de clientes da operação, os clientes tem vendedores associados @stone mesmo sendo um polo franquia, o que significa que aquele Polo Próprio em algum momento virou Polo Franquia.



Canal\_venda: descrição abaixo



Link ABC: cadastro para venda em link de pagamento;

Franquia (ou Polo Franquia): cadastro feito por vendedor de franquia (que possui @querostone.com.br); 

Polo (ou Polo Proprio): cadastro feito por vendedor que atua em polo próprio;

WhatsAppPay: cadastro feito para venda via whatsapp

Tap On Phone: cadastro feito para o cliente vender utilizando o celular como máquina

Key Account: cadastro feito por vendedor stone especializado em grandes contas; 

Comercial: sem informação

Outros: sem informação



Data\_descancelamento: data de reativação de um cadastro de cliente. É o dia que um cliente que já cancelou o cadastro anteriormente foi recadastrado, estando apto a transacionar novamente; 



Responsavel\_descancelamento: novo vendedor, responsável pelo descancelamento e novo responsável pelo cadastro. Observe que esse responsável é diferente do primeiro cadastro, e é o novo responsável pelo cliente. 



Cadastro\_RAV: se o cliente possui antecipação automática pontual (Spot) ou Automatica (Auto).



Mcc\_key: segmento do cliente. Cada número se refere a um segmento de atividade de pessoa jurídica



mcc: descrição do MCC (ramo de atividade do cadastro)



Domicilio\_bancario: banco que o cliente recebe os pagamentos do adquirente Stone.



Data\_criacao\_conta\_stone: data da criação da conta, caso o cliente tenha criado a conta;



Data\_fechamento\_conta\_stone: autoexplicativo



TPV\_estimado: TPV = Total Payments Volume; Se refere ao compromisso (previsao) de volume mensal de pagamentos.



Data\_assinatura\_contrato: quando o contrato de adquirencia foi assinado;



Tipo\_contrato: Com\_multa, contract, term se referem a contratos que preveem multa para não cumprimento ou cancelamento antes do prazo definido em contrato; sem multa ou vazio se refere a cadastro sem contrato; 



TPV\_esperado\_contrato: TPV previsto no contrato assinado; 



Data\_primeira\_ativacao: data que o cliente transacionou pelaa primeira vez; 



Data\_primeira\_transacao: idem para item anterior;



Data\_ultima\_transacao: data da ultima vez que cliente transacionou;



Tem\_seguro: se o cliente tem contratado naquele mês o produto Seguro; Possuimos esse produto, tanto de loja, quanto de vida; esse item se refere a um ou outro;



status\_ba\_m0: se o cliente está ativo no mês vigente;



status\_ba\_m1: se o cliente estava ativo no mês anterior;



dias\_sem\_transacionar: quantos dias o cliente esta sem transacionar;



Todas as 31 colunas abaixo representam o TPV do dia X do mês atual: 



tpv\_d1

tpv\_d2

tpv\_d3

tpv\_d4

tpv\_d5

tpv\_d6

tpv\_d7

tpv\_d8

tpv\_d9

tpv\_d10

tpv\_d11

tpv\_d12

tpv\_d13

tpv\_d14

tpv\_d15

tpv\_d16

tpv\_d17

tpv\_d18

tpv\_d19

tpv\_d20

tpv\_d21

tpv\_d22

tpv\_d23

tpv\_d24

tpv\_d25

tpv\_d26

tpv\_d27

tpv\_d28

tpv\_d29

tpv\_d30

tpv\_d31



tpv\_rolling\_30: TPV "movel" dos últimos 30 dias;



tpv\_rolling\_30\_60: TPV "móvel" dos 30 dias anteriores aos últimos 30 dias; 



Obs: os indicadores que possuem "rolling" no cabeçalho se referem a media móvel, usualmente importantes quando vc analisa a carteira para um dia qualquer do mês; porém, para a analise que faremos, so estamos utilizando a carteira fechada do ultimo dia do mês, e consequentemente do mês fechado.



tpv\_m0: TPV do mês atual



tpv\_m1: TPV do mês anterior



tpv\_m1\_td: TPV "móvel" do mês anterior



tpv\_m2: TPV de dois meses atrás



tpv\_m3: TPV de três meses atrás



tpv\_credito\_m0: TPV considerando apenas pagamentos em Crédito.



tpv\_debito\_m0: TPV considerando apenas pagamentos em Débito. 



tpv\_credito\_m1: TPV crédito do mês anterior;



net\_mdr\_m0: net\_mdr se refere à margem de MDR (Merchant Discount Rate) que compõe a receita do adquirente.



net\_mdr\_credito: net\_mdr referente aos pagamentos de debito



net\_mdr\_debito: net\_mdr referente aos pagamentos de credito



transações: numero de transações total, que se refere a cada vez que um cadastro processa uma venda.



tpv\_antecipado\_m0: TPV que é utilizado para antecipação. Vendas processadas em cartão, especificamente em débito, 

caem na conta do cliente com 30 dias no caso de credito a vista, ou 30, 60, 90, etc no caso de vendas parceladas. A antecipação é um produto adicional para antecipar parte do seu TPV em credito em taxa simples. 



tpv\_antecipado\_auto\_m0: volume TPV antecipado automaticamente no mês atual (M0): automaticamente significa que 100% das vendas em crédito são antecipadas



tpv\_antecipado\_spot\_m0: volume TPV atencipado pontualmente no mês atual (M0)



tpv\_antecipado\_fast\_m0: volume TPV antecipado na modalidade FAST



tpv\_antecipado\_m1: Volume antecipado no mês anterior



tpv\_antecipado\_m2: volume antecipado em M2



tpv\_antecipado\_m3: volume antecipado em M3



rav\_m0: receita gerada por antecipação em M0



rav\_m1: receita gerada por antecipação em M1



funding\_cost\_m0: custo da aquisição de recursos financeiros para antecipação. É equivalente ao "custo de mercadoria". 



funding\_cost\_m1: idem do item anterior para M1



dx\_m0: desconhecido



dx\_m1: desconhecido



duration\_m0: período de parcelamento médio; se o cliente passa apenas credito a vista, o duration será 30; 



Mensalidade\_m0: receita total de mensalidade M0; a mensalidade é cobrada de um cliente por máquina cadastrada ou plano mensal que engloba conjunto de máquinas credenciadas; 



Mensalidade\_m1: receita total de mensalidade M1;



Flag\_IPV: se o cliente naquele mês possui Isenção Por Volume (IPV). Em algumas negociações, o cadastro possui isenção de mensalidade para certos compromissos de TPV. 



Qtd\_equipamentos: quantidade de equipamentos totais instalados no cliente, sejam de POS (Point Of Sales), que são as maquinas de cartão físicas sem fio, geralmente com WiFi ou internet 3G para conexão.



Qtd\_pos: quantidade de POS instaladas no cliente.



Qtd\_pin\_pad: pin\_pad é um equipamento com fio integrado ao computador do cliente.



Receita\_Bruta\_Banking: receita gerada pelo produto Banking:



Receita\_Liquida\_Banking: receita gerada pelo produto Banking descontado do imposto especifico para essa linha;



TPV\_Cartao: O cliente possui um cartão de crédito emitido pela Adquirente Stone. Se ele movimentar esse cartão, o Total em compras realizadas por ele é o valor representado nessa coluna.  



Receita\_interchange: É a receita gerada pelo uso do cartão acima, o TPV\_Cartão.



TPV\_pix\_in\_qr\_code: Total em recebimentos em pagamentos por PIX utilizando o QR Code gerado na POS. Essa modalidade é importante por que gera receita. 



Receita\_pix\_in\_qr\_code: receita gerada pelo TPV de PIX\_in\_qr\_code; OBS: o TPV médio; 



\# as 5 variáveis abaixo se referem a receitas geradas pelo uso da Conta Stone. 

Receita\_Invoice: 

Receita\_boleto:

Receita\_GDA:

Receita\_saques: 

Receita\_recargas:





\# impostos cobrados sobre cada tipo de receita

imposto\_net\_mdr: imposto cobrado sobre o TPV de debito e credito

imposto\_rav: imposto cobrado sobre a receita de antecipação;

imposto mensalidade: imposto cobrado sobre a receita de mensalidade;

imposto banking: imposto cobrado sobre as receitas de banking;



\# abaixo, temos os custos variáveis. Esses custos compõem a coluna CSP, que consolida todos os custos.

custo transações: custos referente a cada transação. Existe um custo fixo por transação mínimo.

custo\_sales\_force: custo do sistema de gestão salesforce para esse cadastro;

custo perdas: custo de perdas relacionados a logística; 

custo chip: custo de chips de 3G quando há POS

custo\_supply: custo variável de logística

custo ineficiência: custo de maquinas paradas na operação;

custo\_rc: custo do atendimento ao cliente via 0800

CSP: consolidação dos custos totais; note que é possível, em alguns meses, haver um custo fixo mínimo: regra que variou ao longo dos anos.





Qtd\_OS\_Baixadas: quantidade de (OS) Ordem de Serviços realizadas. Uma ordem de serviço se refere a um atendimento logístico feito pelo POLO Franquia.



Qtd\_OS\_Atrasadas: OSs que foram atendidas com atraso. Essa variável se refere a certos períodos onde OSs atrasadas geravam multa



Qtd\_OS\_Multas\_Abonadas: OSs que tiveram multas abonadas;



Multa\_Logistica: valor da multa logística por atraso de OS gerada naquele mes



Recorrencia\_Logistica: receita gerada em período que se pagava um valor fixo de logística para certo perfil de TPV, não vigente em todo o periodo



Fee\_Ativacao: bônus gerado de receita para clientes que migravam certo volume. Novamente, essa linha não está mais vigente, mas era vigente por certo período; 



Receita Liquida Total: A receita Liquida total se refere à soma de todas as receitas liquidas (net MDR, RAV ou Antecipação, Mensalidade e Banking)



\# abaixo, iremos falar sobre Rebate

\# o rebate se refere ao % da receita liquida compartilhada com o Polo Franquia.



rebate\_net\_mdr: % da receita MDR 



rebate\_rav: % da receita de RAV



rebate mensalidade: % da receita de mensalidade



rebate banking: % da receita de banking



flo\_rebate\_lucro\_bruto: Receita de Floating. Floating é a receita gerada pelo dinheiro parado na Conta Stone. É uma receita que foi incorporada recentemente pelo polo, e o rebate de floating é o % dessa receita que incorpora ao rebate do Polo Franquia.



Rebate\_Lucro\_Bruto\_m1: rebate do lucro bruto do mês anterior; 



data\_ultima\_atualizacao: 



Rota: a rota é a separação e classificação geográfica a que pertence aquele cadastro dentro do polo. Os nomes mudaram ao longo dos meses. Devemos utilizar como padrão a classificação da carteira do mês mais recente. 



num telefone: numero de telefone do cadastro



ClientKey: desconhecido



CustoBanking: custo do banking; esse custo é deduzido 



\# abaixo, vamos nos referir a alguns indicadores importantes para o modelo de Rebate e um modelo especifico , chamado de 23;



CSP\_23: o CSP desse modelo tinha piso, ou valor mínimo;



Logistica23: qual a receita gerada pela logística nesse modelo;



MultaLogistica23: multa especifica para esse modelo



flag\_client\_meta: se o cliente participa da meta do franqueado;



ReceitaAdesao: receita de Adesão, que é quando o cliente adquire uma maquina. Essa receita s



LucroBrutoM1Modelo23: Lucro Bruto do modelo 23



grupo: desconhecido

net\_mdr\_m1: receita de net\_mdr do mês anterior

Seguro\_Vida\_m0: receita do seguro tipo vida desse mês;

Seguro\_Loja\_m0: receita do seguro tipo loja desse mês;

Lucro\_Bruto\_cia23: Lucro Bruto modelo 23

Receita\_Banking23: receita de Banking 23

Receita\_Seguros23: receita de seguros 23

novas\_receitas23: geralmente, novas receitas se referem a receitas de banking. 

CSP\_sem\_piso: csp sem piso, mais atual que o CSP\_23. 



