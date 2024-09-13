#language: it
@flussi
Funzionalità: Gestione flussi

  @import
  Scenario: L'Operatore carica un flusso contenente nuovi dovuti
    Dato un nuovo flusso A con 3 dovuti di tipo Licenza di Test
    Quando l'Operatore carica il flusso A
    Allora il flusso A è presente nella lista con stato "flusso in caricamento"
    E i dovuti del flusso A sono in stato "predisposto"

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
    Allora il flusso E è presente nella lista con stato "errore caricamento" a causa di "versione tracciato non supportata"
