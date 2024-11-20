#language: it
@riconciliazione
Funzionalità: Riconciliazione

  @rendicontazione
  Scenario: Flusso di rendicontazione
    Dato un dovuto D pagato correttamente compresa la ricezione della RT
    E la generazione del file contenente il flusso di rendicontazione del dovuto D
    Quando il file della rendicontazione viene importato
    Allora il flusso di rendicontazione è caricato
