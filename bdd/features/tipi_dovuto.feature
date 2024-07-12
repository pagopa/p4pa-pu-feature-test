#language: it
@tipi_dovuto
@enteF
Funzionalità: Gestione tipi dovuto

    Contesto:
        Dato l'Ente F censito correttamente

    Scenario: L'Amministratore Globale inserisce un nuovo tipo dovuto
        Dato il tipo dovuto A con macro-area Tributi e tipo servizio TARI
        Quando l'Amministratore Globale inserisce il nuovo tipo dovuto A
        Allora il tipo dovuto A è presente nella lista dei tipi dovuti dell'Ente F
        E di default, il tipo dovuto A è in stato disabilitato

    Scenario: L'Amministratore Globale prova ad inserire un tipo dovuto già presente
        Dato il tipo dovuto B con macro-area Tributi e tipo servizio TARI
        E il tipo dovuto B già inserito nella lista dei tipi dovuti dell'Ente F
        Quando l'Amministratore Globale prova a reinserire il tipo dovuto B
        Allora l'inserimento del tipo dovuto B non va a buon fine a causa di "Tipo dovuto già presente"

    Scenario: L'Amministratore Globale abilita un tipo dovuto per l'Ente
        Dato il tipo dovuto C con macro-area Corpo di Polizia e tipo servizio Multe
        E il tipo dovuto C già inserito nella lista dei tipi dovuti dell'Ente F
        Quando l'Amministratore Globale abilita il tipo dovuto C
        Allora il tipo dovuto C è in stato abilitato

    Scenario: L'Amministratore Globale disabilita un tipo dovuto per l'Ente
        Dato il tipo dovuto D con macro-area Sport e tipo servizio Impianti sportivi
        E il tipo dovuto D già inserito e abilitato nella lista dei tipi dovuti dell'Ente F
        Quando l'Amministratore Globale disabilita il tipo dovuto D
        Allora il tipo dovuto D è in stato disabilitato

    @notifica_io
    Scenario: L'Amministratore Globale modifica un tipo dovuto abilitando l'invio delle notifiche di avviso su IO
        Dato il tipo dovuto E con macro-area Varie e tipo servizio Parcheggi
        E il tipo dovuto E già inserito nella lista dei tipi dovuti dell'Ente F
        Quando l'Amministratore Globale modifica il tipo dovuto E abilitando le notifiche di avviso su IO
        Allora per il tipo dovuto E le notifiche sono abilitate, grazie alla creazione di un servizio su IO

    Scenario: L'Amministratore Globale cancella un tipo dovuto
        Dato il tipo dovuto F con macro-area Servizi idrici e tipo servizio Acquedotto
        E il tipo dovuto F già inserito nella lista dei tipi dovuti dell'Ente F
        Quando l'Amministratore Globale cancella il tipo dovuto F
        Allora il tipo dovuto F non è più presente tra i tipi dovuti dell'Ente F

#    @bug
#    Scenario: L'Amministratore Globale prova a modificare il codice di un tipo dovuto
#        Dato il tipo dovuto G con macro-area Sport e tipo servizio Impianti sportivi
#        E il tipo dovuto G già inserito nella lista dei tipi dovuti dell'Ente F
#        Quando l'Amministratore Globale prova a modificare il codice del tipo dovuto G
#        Allora la modifica del tipo dovuto G non va a buon fine a causa di "richiesta non valida"

#    @admin_ente
#    @bug
#    Scenario: L'Amministratore Ente prova ad inserire un nuovo tipo dovuto
#        Dato il tipo dovuto G con macro-area Tributi e tipo servizio TARI
#        Quando l'Amministratore Ente prova ad inserire il nuovo tipo dovuto G
#        Allora l'inserimento del tipo dovuto G non va a buon fine a causa di "Utente non autorizzato"