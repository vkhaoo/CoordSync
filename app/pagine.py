"""
Quanto grande e' una pagina di risultati, tenuto in un posto solo.

Gli elenchi che crescono senza limite — i lavori di un progetto, lo storico di
una macchina — non si possono scaricare tutti: e' una lentezza che peggiora
col tempo, e si presenta proprio quando l'app comincia a essere usata sul
serio. Arrivano a pagine, e quanti ce ne sono in tutto viaggia
nell'intestazione X-Totale, cosi' chi legge sa se ha senso chiedere il resto.

PERCHE' UN'INTESTAZIONE e non un oggetto {elementi, totale}: la risposta resta
una lista, quindi chi la legge non deve cambiare, e le due cose restano
separate — i dati nel corpo, il conteggio fra le informazioni di servizio.

50 e' una scelta pratica: piu' di quanti se ne guardano in una schermata, meno
di quanti ne rendano pesante la risposta. Il tetto a 200 esiste perche' il
limite lo sceglie chi chiama, e senza un massimo basterebbe chiedere
limite=100000 per riportare il problema esattamente dov'era.
"""

PAGINA = 50
MASSIMO_PAGINA = 200
