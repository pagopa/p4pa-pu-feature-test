#language: it
@dovuti
@gpd
Funzionalità: Gestione dovuti

  @avviso
  Scenario: L'Operatore inserisce un nuovo dovuto e viene creata una posizione debitoria
    Dato il dovuto A di tipo Licenza di Test del valore di 50.00 euro per la cittadina Maria
    Quando l'Operatore inserisce il dovuto A con generazione avviso
    Allora il dovuto A è in stato "da pagare"
    E una nuova posizione debitoria relativa al dovuto A risulta creata
    E l'Operatore può scaricare l'avviso di pagamento per il dovuto A

  Scenario: L'Operatore annulla un dovuto e viene rimossa la posizione debitoria
    Dato il dovuto B di tipo Licenza di Test del valore di 75.00 euro per la cittadina Maria
    E il dovuto B inserito correttamente con la relativa posizione debitoria
    Quando l'Operatore annulla il dovuto B
    Allora il dovuto B è in stato "annullato" nell'archivio
    E la posizione debitoria relativa al dovuto B non è più presente

  Scenario: L'Operatore modifica un dovuto e viene modificata anche la posizione debitoria
    Dato il dovuto C di tipo Licenza di Test del valore di 80.00 euro per la cittadina Maria
    E il dovuto C inserito correttamente con la relativa posizione debitoria
    Quando l'Operatore modifica il valore dell'importo del dovuto C da 80.00 a 105.50 euro
    Allora l'importo della posizione debitoria relativa al dovuto C è ora di 105.50 euro

  @pagamento
  @RT
  Scenario: L'Operatore inserisce un nuovo dovuto e il pagamento avviene con successo
    Dato il dovuto D di tipo Licenza di Test del valore di 75.50 euro per la cittadina Maria
    E il dovuto D inserito correttamente con la relativa posizione debitoria
    Quando la cittadina Maria effettua il pagamento del dovuto D
    Allora il dovuto D è in stato "pagato" nell'archivio
    E l'Operatore può scaricare la ricevuta di pagamento effettuato per il dovuto D

  @multibeneficiario
  Scenario: L'Operatore inserisce un nuovo dovuto con multibeneficiario
    Dato il dovuto E di tipo Licenza di Test del valore di 65.00 euro per la cittadina Maria
    E l'aggiunta dell'Ente intermediato 1 come altro beneficiario del dovuto E con importo di 45.00 euro
    Quando l'Operatore inserisce il dovuto E con generazione avviso e con multibeneficiario
    Allora il dovuto E è in stato "da pagare"
    E una nuova posizione debitoria relativa al dovuto E risulta creata con il dettaglio dei due enti beneficiari

  Scenario: L'Amministratore Ente prova ad inserire un nuovo dovuto con tipo dovuto su cui non è abilitato
    Dato il tipo dovuto Licenza di Test disabilitato per l'utente Amministratore Ente
    E il dovuto G di tipo Licenza di Test del valore di 83.55 euro per la cittadina Maria
    Quando l'Amministratore Ente prova ad inserire il dovuto G
    Allora l'inserimento del nuovo dovuto non va a buon fine a causa di "tipo dovuto non attivo per l'operatore"

  Schema dello scenario: L'Operatore prova ad inserire un nuovo dovuto senza <dato>
    Dato il dovuto H di tipo Licenza di Test del valore di 83.55 euro per la cittadina Maria
    Quando l'Operatore prova ad inserire il dovuto H senza <dato>
    Allora l'inserimento del nuovo dovuto non va a buon fine a causa di "<causa errore>"

    Esempi: Campi errati
            | dato           | causa errore                |
            | codice fiscale | codice fiscale obbligatorio |
            | causale        | causale obbligatoria        |

  Scenario: L'Operatore modifica un dovuto scaduto aggiornando la data di scadenza
    Dato il dovuto X di tipo Licenza di Test per la cittadina Maria in stato scaduto
    Quando l'Operatore proroga la data di scadenza del dovuto X di 10 giorni
    Allora la data di scadenza del dovuto X è stata aggiornata correttamente
    E il dovuto X è in stato "da pagare"