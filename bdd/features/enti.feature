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
    Schema dello scenario: L'Amministratore Globale prova ad inserire un nuovo Ente con valore del dato <dato errato> non valido
        Dato un nuovo Ente di tipo Regione con codice IPA W
        Quando l'Amministratore Globale prova ad inserire i dati dell'Ente W con valore del dato <dato errato> non valido
        Allora l'inserimento non va a buon fine a causa di "<causa errore>"

        Esempi: Campi errati
            | dato errato    | causa errore            |
            | email          | E-mail invalida         |
            | codice fiscale | Codice fiscale invalido |

    @inserimento
    @admin_ente
    Scenario: L'Amministratore Ente prova ad inserire un nuovo Ente
        Dato un nuovo Ente di tipo Comune con codice IPA X
        Quando l'Amministratore Ente prova ad inserire i dati dell'Ente X
        Allora l'inserimento non va a buon fine a causa di "Utente non autorizzato"

    @inserimento
    @operatore
    Scenario: L'Operatore prova ad inserire un nuovo Ente
        Dato un nuovo Ente di tipo Comune con codice IPA X
        Quando l'Operatore prova ad inserire i dati dell'Ente X
        Allora l'inserimento non va a buon fine a causa di "Utente non autorizzato"

    @modifica
    @admin_globale
    Schema dello scenario: L'Amministratore Globale modifica <dato> di un Ente precedentemente inserito
        Dato un Ente di tipo Provincia con codice IPA <etichetta> già inserito correttamente
        Quando l'Amministratore Globale modifica <dato> dell'Ente <etichetta> in <nuovo valore>
        Allora <dato> dell'Ente <etichetta> risulta correttamente modificato

        Esempi: Valori da modificare
            | etichetta | dato     | nuovo valore   |
            | A         | lo stato | pre-esercizio  |
            | B         | il tipo  | Comune         |

    @modifica
    @admin_globale
    Schema dello scenario: L'Amministratore Globale prova a modificare <dato> di un Ente con valore non valido
        Dato un Ente di tipo Comune con codice IPA <etichetta> già inserito correttamente
        Quando l'Amministratore Globale prova a modificare <dato> dell'Ente <etichetta> in <nuovo valore>
        Allora la modifica non va a buon fine a causa di "<causa errore>"

        Esempi: Valori da modificare
            | etichetta | dato                    | nuovo valore    | causa errore                 |
            | C         | la email                | email$email.it  | E-mail invalida              |
            | D         | il codice segregazione  | 1234            | Codice segregazione invalido |

    @funzionalita
    @admin_globale
    Scenario: L'Amministratore Globale attiva la funzionalità Notifica Avvisi IO per un Ente
        Dato un Ente di tipo Comune con codice IPA E già inserito correttamente
        Quando l'Amministratore Globale attiva la funzionalità Notifica Avvisi IO per l'Ente E
        Allora l'Ente E ha la funzionalità di Notifica Avvisi IO attivata

    @funzionalita
    @admin_globale
    Scenario: L'Amministratore Globale prova ad attivare una funzionalità non esistente per un Ente
        Dato un Ente di tipo Comune con codice IPA F già inserito correttamente
        Quando l'Amministratore Globale prova ad attivare la funzionalità Test per l'Ente F
        Allora l'attivazione non va a buon fine a causa di "Funzionalità non esistente"

    @funzionalita
    @admin_globale
    Scenario: L'Amministratore Globale disattiva la funzionalità Avviso Digitale per un Ente
        Dato un Ente di tipo Comune con codice IPA G già inserito correttamente
        E l'Amministratore Globale che attiva correttamente la funzionalità Avviso Digitale per l'Ente G
        Quando l'Amministratore Globale disattiva la funzionalità Avviso Digitale per l'Ente G
        Allora l'Ente G ha la funzionalità di Avviso Digitale disattivata
