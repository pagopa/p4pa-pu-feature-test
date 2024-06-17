#language: it
@ente
Funzionalità: Gestione enti

    @inserimento
    Scenario: L'Amministratore Globale inserisce un nuovo Ente
        Dato un nuovo Ente di tipo Comune con codice IPA X
        Quando l'Amministratore Globale inserisce correttamente i dati dell'Ente X
        Allora l'Ente X è in stato "inserito"
        E l'Ente X ha la funzionalità di Pagamento Spontaneo attivata
