#language: it
@dovuti
@gpd
Funzionalità: Gestione dovuti

  Scenario: L'Operatore inserisce un nuovo dovuto e viene creata una posizione debitoria
    Dato il dovuto A di tipo Licenza di Test del valore di 50 euro per la cittadina Maria
    Quando l'Operatore inserisce il dovuto A con generazione avviso
    Allora il dovuto A è in stato "da pagare"
    E una nuova posizione debitoria relativa al dovuto A risulta creata

  Scenario: L'Operatore annulla un dovuto e viene rimossa la posizione debitoria
    Dato il dovuto B di tipo Licenza di Test del valore di 75 euro per la cittadina Maria
    E il dovuto B inserito correttamente con la relativa posizione debitoria
    Quando l'Operatore annulla il dovuto B
    Allora il dovuto B è in stato "annullato" nell'archivio
    E la posizione debitoria relativa al dovuto B non è più presente

  Scenario: L'Operatore modifica un dovuto e viene modificata anche la posizione debitoria
    Dato il dovuto C di tipo Licenza di Test del valore di 80 euro per la cittadina Maria
    E il dovuto C inserito correttamente con la relativa posizione debitoria
    Quando l'Operatore modifica il valore dell'importo del dovuto C da 80 a 105.5 euro
    Allora l'importo della posizione debitoria relativa al dovuto C è ora di 105.5 euro
