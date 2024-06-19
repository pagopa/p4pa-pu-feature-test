#language: it
@enti
Funzionalità: Gestione enti

    @inserimento
    @admin_globale
    Scenario: L'Amministratore Globale inserisce un nuovo Ente
        Dato un nuovo Ente di tipo Comune con codice IPA X
        Quando l'Amministratore Globale inserisce correttamente i dati dell'Ente X
        Allora l'Ente X è in stato "inserito"
        E l'Ente X ha la funzionalità di Pagamento Spontaneo attivata

    @logo
    @admin_globale
    Scenario: L'Amministratore Globale inserisce un nuovo Ente, avente un logo
        Dato un nuovo Ente di tipo Provincia con codice IPA Y
        E l'Amministratore Globale che inserisce correttamente i dati dell'Ente Y
        Quando l'Amministratore Globale aggiunge il logo all'Ente Y
        Allora l'Ente Y presenta il suo logo correttamente

    @inserimento
    @admin_globale
    Scenario: L'Amministratore Globale prova ad inserire un Ente con codice IPA già presente
        Dato un Ente di tipo Comune con codice IPA Z già inserito correttamente
        Quando l'Amministratore Globale prova a reinserire i dati dell'Ente Z
        Allora l'inserimento non va a buon fine a causa di "Ente già presente"

    @inserimento
    @admin_globale
    Schema dello scenario: L'Amministratore Globale prova ad inserire un nuovo Ente con email o codice fiscale non validi
        Dato un nuovo Ente di tipo Regione con codice IPA W
        Quando l'Amministratore Globale prova ad inserire i dati dell'Ente W con <dato errato> non valido
        Allora l'inserimento non va a buon fine a causa di "<causa errore>"

        Esempi: Campi errati
            | dato errato    | causa errore            |
            | email          | E-mail invalida         |
            | codice fiscale | Codice fiscale invalido |