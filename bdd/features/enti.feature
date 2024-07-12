#language: it
@enti
@enteE
Funzionalità: Gestione enti

    @inserimento
    @admin_globale
    Scenario: L'Amministratore Globale inserisce un nuovo Ente
        Dato un nuovo Ente di tipo Comune con codice IPA A
        Quando l'Amministratore Globale inserisce correttamente i dati dell'Ente A
        Allora l'Ente A è in stato "inserito"
        E l'Ente A ha la funzionalità di Pagamento Spontaneo attivata

    @logo
    @admin_globale
    Scenario: L'Amministratore Globale inserisce un nuovo Ente, avente un logo
        Dato un nuovo Ente di tipo Provincia con codice IPA B
        E l'Amministratore Globale che inserisce correttamente i dati dell'Ente B
        Quando l'Amministratore Globale aggiunge il logo all'Ente B
        Allora l'Ente B presenta il suo logo correttamente

    @inserimento
    @admin_globale
    Scenario: L'Amministratore Globale prova ad inserire un Ente con codice IPA già presente
        Dato un Ente di tipo Comune con codice IPA C già inserito correttamente
        Quando l'Amministratore Globale prova a reinserire i dati dell'Ente C
        Allora l'inserimento non va a buon fine a causa di "Ente già presente"

    @inserimento
    @admin_globale
    Schema dello scenario: L'Amministratore Globale prova ad inserire un nuovo Ente con valore del dato <dato errato> non valido
        Dato un nuovo Ente di tipo Regione con codice IPA D
        Quando l'Amministratore Globale prova ad inserire i dati dell'Ente D con valore del dato <dato errato> non valido
        Allora l'inserimento non va a buon fine a causa di "<causa errore>"

        Esempi: Campi errati
            | dato errato    | causa errore            |
            | email          | E-mail invalida         |
            | codice fiscale | Codice fiscale invalido |

    @inserimento
    @admin_ente
    Scenario: L'Amministratore Ente prova ad inserire un nuovo Ente
        Dato un nuovo Ente di tipo Comune con codice IPA A
        Quando l'Amministratore Ente prova ad inserire i dati dell'Ente A
        Allora l'inserimento non va a buon fine a causa di "Utente non autorizzato"

    @inserimento
    @operatore
    Scenario: L'Operatore prova ad inserire un nuovo Ente
        Dato un nuovo Ente di tipo Comune con codice IPA A
        Quando l'Operatore prova ad inserire i dati dell'Ente A
        Allora l'inserimento non va a buon fine a causa di "Utente non autorizzato"

    @modifica
    @admin_globale
    Schema dello scenario: L'Amministratore Globale modifica <dato> di un Ente precedentemente inserito
        Dato l'Ente E censito correttamente
        Quando l'Amministratore Globale modifica <dato> dell'Ente E in <nuovo valore>
        Allora <dato> dell'Ente E risulta correttamente modificato

        Esempi: Valori da modificare
            | dato     | nuovo valore   |
            | lo stato | pre-esercizio  |
            | il tipo  | Comune         |

    @modifica
    @admin_globale
    Schema dello scenario: L'Amministratore Globale prova a modificare <dato> di un Ente con valore non valido
        Dato l'Ente E censito correttamente
        Quando l'Amministratore Globale prova a modificare <dato> dell'Ente E in <nuovo valore>
        Allora la modifica non va a buon fine a causa di "<causa errore>"

        Esempi: Valori da modificare
            | dato                    | nuovo valore    | causa errore                 |
            | la email                | email$email.it  | E-mail invalida              |
            | il codice segregazione  | 1234            | Codice segregazione invalido |

    @funzionalita
    @admin_globale
    Scenario: L'Amministratore Globale attiva la funzionalità Notifica Avvisi IO per un Ente
        Dato l'Ente E censito correttamente
        Quando l'Amministratore Globale attiva la funzionalità Notifica Avvisi IO per l'Ente E
        Allora l'Ente E ha la funzionalità di Notifica Avvisi IO attivata

    @funzionalita
    @admin_globale
    Scenario: L'Amministratore Globale prova ad attivare una funzionalità non esistente per un Ente
        Dato l'Ente E censito correttamente
        Quando l'Amministratore Globale prova ad attivare la funzionalità Test per l'Ente E
        Allora l'attivazione non va a buon fine a causa di "Funzionalità non esistente"

    @funzionalita
    @admin_globale
    Scenario: L'Amministratore Globale disattiva la funzionalità Avviso Digitale per un Ente
        Dato l'Ente E censito correttamente
        E l'Amministratore Globale che attiva correttamente la funzionalità Avviso Digitale per l'Ente E
        Quando l'Amministratore Globale disattiva la funzionalità Avviso Digitale per l'Ente E
        Allora l'Ente E ha la funzionalità di Avviso Digitale disattivata
