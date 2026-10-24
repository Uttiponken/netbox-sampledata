"""
The municipalities of Stockholm County that can own ducts on the metro ring: party code -> (full name, tenant slug, short name).

The code is the municipality's name in lower case without å/ä/ö, which is how data/metro.py names the owner of a leg.
Only the ones the ring actually passes through become tenants (data/organization.py); the others are here so a
change of route needs no other edit.
"""

NAMES = {
    "sollentuna": ("Sollentuna kommun", "sollentuna-kommun", "Sollentuna"),
    "danderyd": ("Danderyds kommun", "danderyds-kommun", "Danderyd"),
    "lidingo": ("Lidingö stad", "lidingo-stad", "Lidingö"),
    "nacka": ("Nacka kommun", "nacka-kommun", "Nacka"),
    "stockholm": ("Stockholms stad", "stockholms-stad", "Stockholm"),
    "ekero": ("Ekerö kommun", "ekero-kommun", "Ekerö"),
    "botkyrka": ("Botkyrka kommun", "botkyrka-kommun", "Botkyrka"),
    "huddinge": ("Huddinge kommun", "huddinge-kommun", "Huddinge"),
    "sodertalje": ("Södertälje kommun", "sodertalje-kommun", "Södertälje"),
    "solna": ("Solna stad", "solna-stad", "Solna"),
    "sundbyberg": ("Sundbybergs stad", "sundbybergs-stad", "Sundbyberg"),
    "jarfalla": ("Järfälla kommun", "jarfalla-kommun", "Järfälla"),
    "salem": ("Salems kommun", "salems-kommun", "Salem"),
    "upplands-bro": ("Upplands-Bro kommun", "upplands-bro-kommun", "Upplands-Bro"),
    "taby": ("Täby kommun", "taby-kommun", "Täby"),
    "nykvarn": ("Nykvarns kommun", "nykvarns-kommun", "Nykvarn"),
    "haninge": ("Haninge kommun", "haninge-kommun", "Haninge"),
    "tyreso": ("Tyresö kommun", "tyreso-kommun", "Tyresö"),
    "varmdo": ("Värmdö kommun", "varmdo-kommun", "Värmdö"),
    "vallentuna": ("Vallentuna kommun", "vallentuna-kommun", "Vallentuna"),
}
