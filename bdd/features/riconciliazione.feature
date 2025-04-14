#language: it
@riconciliazione
Funzionalità: Riconciliazione

  @rendicontazione
  Scenario: Flusso di rendicontazione
    Dato il dovuto 1 pagato correttamente compresa la ricezione della RT
    E il dovuto 2 pagato correttamente compresa la ricezione della RT
    E la generazione del file contenente il flusso di rendicontazione relativo ai dovuti 1 e 2
    Quando il file della rendicontazione viene importato
    Allora il flusso di rendicontazione è caricato e comprende i dovuti 1 e 2
    # check classificazione RT_IUF

  @tesoreria
  Scenario: Flusso di tesoreria
    Dato il dovuto 1 pagato correttamente compresa la ricezione della RT
    E il flusso di rendicontazione relativo al dovuto 1 importato correttamente
    E la generazione del file di tesoreria correlato alla rendicontazione
    Quando il file della tesoreria viene importato
    Allora il flusso di tesoreria è caricato con lo IUF della rendicontazione
    # check classificazione RT_IUF_TES
