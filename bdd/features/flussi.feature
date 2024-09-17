#language: it
@flussi
Funzionalità: Gestione flussi

  @import
  Scenario: L'Operatore carica un flusso contenente nuovi dovuti
    Dato un nuovo flusso A con 3 dovuti di tipo Licenza di Test
    Quando l'Operatore carica il flusso A
    Allora il flusso A è presente nella lista con stato "caricato"
    E i dovuti inseriti tramite flusso A sono in stato "da pagare"

  @import
  @multibeneficiario
  Scenario: L'Operatore carica un flusso contenente nuovi dovuti di cui uno multibeneficiario
    Dato un nuovo flusso B con 3 dovuti di tipo Licenza di Test e versione tracciato "1_4"
    E un dovuto 4 di tipo multibeneficiario aggiunto nel flusso B
    Quando l'Operatore carica il flusso B
    Allora il flusso B è presente nella lista con stato "flusso in caricamento"
    E i dovuti inseriti tramite flusso B sono in stato "predisposto"
    E il dovuto 4 del flusso B nel dettaglio presenta due beneficiari

  @export_rt
  Scenario: L'Operatore prenota l'export delle ricevute telematiche e verifica il pagamento di un dovuto
    Dato il dovuto D di tipo Licenza di Test del valore di 51.50 euro per la cittadina Maria
    E il dovuto D inserito e pagato correttamente dalla cittadina Maria
    Quando l'Operatore prenota l'export delle ricevute telematiche
    Allora il flusso RT prenotato è visibile nella lista
    E l'Operatore scaricando il flusso verifica il dettaglio del dovuto D pagato

  Scenario: L'Operatore prova a caricare un flusso con lo stesso nome di un file già caricato
    Dato un nuovo flusso B con 3 dovuti di tipo Licenza di Test
    E l'Operatore che carica correttamente il flusso B
    E un nuovo flusso C con 2 dovuti di tipo Licenza di Test
    Quando l'Operatore prova a caricare il flusso C con lo stesso nome del flusso B
    Allora il caricamento del flusso C non va a buon fine a causa di "flusso esistente con stesso nome"

  Scenario: L'Operatore prova a caricare un flusso con il nome del file che non inizia con il codice ipa corretto
    Dato un nuovo flusso D con 3 dovuti di tipo Licenza di Test
    Quando l'Operatore prova a caricare il flusso D con nome del file che non inizia con il codice ipa
    Allora il caricamento del flusso D non va a buon fine a causa di "il nome del file deve iniziare con il codice ipa"

  Scenario: L'Operatore prova a caricare un flusso con la 'versione tracciato' non valida
    Dato un nuovo flusso E con 4 dovuti di tipo Licenza di Test e versione tracciato "1_45"
    Quando l'Operatore carica il flusso E
    Allora il flusso E è presente nella lista con stato "errore" a causa di "versione tracciato non supportata"

  Scenario: L'Operatore carica un flusso contenente un dovuto senza codice fiscale
    Dato un nuovo flusso F con 3 dovuti di tipo Licenza di Test
    E un altro dovuto aggiunto nel flusso F a cui non è stato inserito il codice fiscale
    Quando l'Operatore carica il flusso F
    Allora il flusso F è in stato "caricato" ma con 1 scarto a causa di "codice fiscale non presente"

  Schema dello scenario: L'Operatore prova a prenotare l'export delle RT con un <dato errato> non corretto
    Dato il dovuto D di tipo Licenza di Test del valore di 61.50 euro per la cittadina Maria
    E il dovuto D inserito e pagato correttamente dalla cittadina Maria
    Quando l'Operatore prova a prenotare l'export delle ricevute telematiche inserendo un <dato errato> invalido
    Allora la prenotazione dell'export delle RT non va a buon fine a causa di "<causa errore>"

    Esempi: Campi errati
        | dato errato        | causa errore            |
        | intervallo di date | date non corrette       |
        | tipo dovuto        | tipo dovuto non trovato |
