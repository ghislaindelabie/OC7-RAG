# Demo Scenarios - OC7-RAG

**Purpose**: Demonstrate the capabilities of the RAG system with realistic queries
**Target Audience**: New users, stakeholders, and evaluators
**Last Updated**: 2026-02-05

---

## How to Use These Scenarios

Each scenario includes:
- **Question**: The user query in French
- **Expected Behavior**: What the system should do
- **RAG Method**: Recommended method for best results
- **Sample Response**: What kind of answer to expect

You can test these via:
- **Web Interface**: http://188.34.205.146:8000/
- **API**: `curl -X POST http://188.34.205.146:8000/api/v1/ask -H "Content-Type: application/json" -d '{"question": "..."}'`
- **Notebook**: `notebooks/01_baseline_rag.ipynb`

---

## Scenario 1: Location-Specific Concert Query

**Category**: Factual
**Complexity**: Simple
**Query Type**: Location + Event Type

### Question
```
Quels concerts à Chambéry ce weekend?
```

### Expected Behavior
- Identify location: Chambéry (Savoie, 73)
- Identify event type: concerts
- Identify time: "ce weekend" (this weekend)
- Retrieve relevant concert events
- Present 3-5 results with dates, venues, and details

### Recommended Method
**Hybrid** - Combines semantic understanding ("concerts") with keyword matching ("Chambéry")

### Sample Response Structure
```
Voici les concerts prévus à Chambéry ce weekend:

1. **Festival Jazz à Chambéry**
   - Date: Samedi 10 février, 20h30
   - Lieu: Salle Malraux
   - Type: Concert de jazz

2. **Concert Symphonique**
   - Date: Dimanche 11 février, 15h00
   - Lieu: Théâtre Charles Dullin
   - Type: Musique classique

...
```

---

## Scenario 2: Family Activity Search

**Category**: Complex
**Complexity**: Multi-criteria
**Query Type**: Audience + Location + Time

### Question
```
Activités familiales en Haute-Savoie pour les vacances d'hiver
```

### Expected Behavior
- Identify audience: families (all ages)
- Identify location: Haute-Savoie (74)
- Identify time: winter vacation period
- Filter for family-friendly events
- Present diverse activities (not just one type)

### Recommended Method
**Advanced** - Complex query benefits from query analysis and reranking

### Sample Response Structure
```
Voici des activités familiales en Haute-Savoie pendant les vacances:

1. **Spectacle de marionnettes à Annecy**
   - Public: Enfants 3-10 ans
   - Date: Tous les mercredis de février
   - Lieu: Théâtre des Marionnettes

2. **Atelier de fabrication de pain à Megève**
   - Public: Familles
   - Date: Samedis 10, 17, 24 février
   - Lieu: Ferme pédagogique du Mont Blanc

...
```

---

## Scenario 3: Event Type Discovery

**Category**: Factual
**Complexity**: Simple
**Query Type**: Event Type

### Question
```
Quels sont les festivals de musique dans le 38 cet été?
```

### Expected Behavior
- Identify event type: music festivals
- Identify location: département 38 (Isère)
- Identify time: summer (June-August)
- List various music festivals
- Include different music genres

### Recommended Method
**Hybrid** - Good for type + location queries

### Sample Response Structure
```
Voici les festivals de musique en Isère cet été:

1. **Festival de Jazz de Grenoble**
   - Dates: 15-20 juin 2026
   - Lieu: Parc Paul Mistral, Grenoble
   - Genre: Jazz et musiques du monde

2. **Cabaret Frappé**
   - Dates: 10-15 juillet 2026
   - Lieu: Parc Albert Michallon, Grenoble
   - Genre: Rock, électro, hip-hop

...
```

---

## Scenario 4: Date-Specific Query

**Category**: Factual
**Complexity**: Simple
**Query Type**: Date + Location

### Question
```
Que faire à Annecy le 14 juillet?
```

### Expected Behavior
- Identify specific date: July 14 (Bastille Day)
- Identify location: Annecy
- Consider special events for national holiday
- Present all event types (concerts, fireworks, parades)

### Recommended Method
**Basic** - Simple query with clear criteria

### Sample Response Structure
```
Voici les événements à Annecy le 14 juillet:

1. **Fête Nationale - Feu d'artifice**
   - Heure: 22h30
   - Lieu: Jardins de l'Europe, bord du lac
   - Type: Spectacle pyrotechnique

2. **Concert gratuit de musique classique**
   - Heure: 19h00
   - Lieu: Jardins de l'Europe
   - Type: Orchestre symphonique

...
```

---

## Scenario 5: Vague Query Requiring Clarification

**Category**: Vague
**Complexity**: Ambiguous
**Query Type**: Underspecified

### Question
```
Y a-t-il quelque chose d'intéressant?
```

### Expected Behavior
- Recognize vague query
- Request clarification
- Suggest specific query types
- Provide examples of what can be asked

### Recommended Method
**Advanced** - Query analysis detects vague queries

### Sample Response Structure
```
Je peux vous aider à trouver des événements culturels, mais votre question est un peu générale.

Pouvez-vous préciser:
- 🎭 Quel type d'événement? (concert, théâtre, exposition, festival...)
- 📍 Dans quelle région? (Savoie, Haute-Savoie, Isère)
- 📅 Pour quelle période? (ce weekend, ce mois-ci, cet été...)

Par exemple:
- "Quels concerts à Chambéry ce weekend?"
- "Expositions à Grenoble en février"
- "Festivals d'été en Haute-Savoie"
```

---

## Scenario 6: Off-Topic Query

**Category**: Off-topic
**Complexity**: N/A
**Query Type**: Not about events

### Question
```
Quelle est la capitale de la France?
```

### Expected Behavior
- Detect off-topic query
- Politely decline to answer
- Redirect to event-related topics
- Provide examples of valid questions

### Recommended Method
**Any** - Query analysis works across all methods

### Sample Response Structure
```
Je suis désolé, mais je suis spécialisé dans les événements culturels en Savoie, Haute-Savoie et Isère. Je ne peux pas répondre aux questions générales.

Je peux vous aider à trouver:
- 🎭 Des concerts, spectacles, et pièces de théâtre
- 🎨 Des expositions et événements culturels
- 🎪 Des festivals et manifestations
- 👨‍👩‍👧 Des activités familiales

Posez-moi une question sur les événements dans ces départements!
```

---

## Scenario 7: Genre-Specific Search

**Category**: Factual
**Complexity**: Medium
**Query Type**: Genre + Location

### Question
```
Spectacles de théâtre contemporain à Grenoble ce mois-ci
```

### Expected Behavior
- Identify type: theater
- Identify genre: contemporary
- Identify location: Grenoble (Isère, 38)
- Identify time: current month
- Filter for contemporary (not classical) theater

### Recommended Method
**Hybrid** - Benefits from both semantic and keyword matching

### Sample Response Structure
```
Voici les spectacles de théâtre contemporain à Grenoble ce mois-ci:

1. **"La Machine de Turing"**
   - Dates: 5-8 février
   - Lieu: MC2 Grenoble
   - Genre: Théâtre contemporain
   - Durée: 1h45

2. **"Un fil à la patte"**
   - Dates: 12-15 février
   - Lieu: Théâtre Prémol
   - Genre: Comédie contemporaine
   - Durée: 1h30

...
```

---

## Scenario 8: Price-Sensitive Query

**Category**: Complex
**Complexity**: Multi-criteria
**Query Type**: Price + Type + Location

### Question
```
Événements gratuits à Annecy ce weekend
```

### Expected Behavior
- Identify price: free
- Identify location: Annecy
- Identify time: this weekend
- Filter for free admission events
- Present diverse event types

### Recommended Method
**Advanced** - Benefits from filtering and reranking

### Sample Response Structure
```
Voici les événements gratuits à Annecy ce weekend:

1. **Visite guidée de la vieille ville**
   - Date: Samedi 10h00
   - Lieu: Office de tourisme d'Annecy
   - Tarif: Gratuit (inscription recommandée)

2. **Concert au Haras**
   - Date: Dimanche 17h00
   - Lieu: Le Haras d'Annecy
   - Tarif: Entrée libre

...
```

---

## Scenario 9: Audience-Specific Query

**Category**: Complex
**Complexity**: Audience targeting
**Query Type**: Age + Type + Location

### Question
```
Spectacles pour enfants de 5 ans en Savoie
```

### Expected Behavior
- Identify target age: 5 years old
- Identify location: Savoie (73)
- Filter age-appropriate events
- Present shows suitable for young children

### Recommended Method
**Advanced** - Age filtering benefits from query analysis

### Sample Response Structure
```
Voici des spectacles adaptés aux enfants de 5 ans en Savoie:

1. **"Boucle d'Or et les trois ours"**
   - Public: 3-7 ans
   - Date: Samedi 15h00
   - Lieu: Théâtre Espace Malraux, Chambéry
   - Durée: 45 minutes

2. **Spectacle de magie "Abracadabra"**
   - Public: 4-8 ans
   - Date: Dimanche 10h30
   - Lieu: Salle Polyvalente, Aix-les-Bains
   - Durée: 1h00

...
```

---

## Scenario 10: Multi-Location Query

**Category**: Complex
**Complexity**: Multiple locations
**Query Type**: Type + Multiple Locations

### Question
```
Festivals en Savoie et Haute-Savoie en juillet
```

### Expected Behavior
- Identify event type: festivals
- Identify locations: Savoie (73) and Haute-Savoie (74)
- Identify time: July
- Present festivals from both departments
- Organize by date or location

### Recommended Method
**Hybrid** - Good for multi-location queries

### Sample Response Structure
```
Voici les festivals en Savoie et Haute-Savoie en juillet:

**Savoie (73)**:
1. **Festival de Jazz d'Aix-les-Bains**
   - Dates: 5-10 juillet
   - Lieu: Aix-les-Bains

**Haute-Savoie (74)**:
2. **Festival des Nuits de la Citadelle**
   - Dates: 15-20 juillet
   - Lieu: Annecy

3. **Festival de Musique Baroque**
   - Dates: 22-28 juillet
   - Lieu: Evian-les-Bains

...
```

---

## Testing Tips

### For Developers
```bash
# Test via API
for scenario in "Quels concerts à Chambéry ce weekend?" \
                "Activités familiales en Haute-Savoie" \
                "Quelle est la capitale de la France?"; do
    echo "Testing: $scenario"
    curl -X POST http://localhost:8000/api/v1/ask \
      -H "Content-Type: application/json" \
      -d "{\"question\": \"$scenario\"}" \
      | python3 -m json.tool
    echo "---"
done
```

### For Manual Testing
1. Open web interface: http://188.34.205.146:8000/
2. Try each scenario
3. Compare responses to expected behavior
4. Note any discrepancies for improvement

### For Evaluation
Use the test dataset in `tests/test_data/test_questions.csv` which includes 56 annotated questions similar to these scenarios.

---

## Conclusion

These scenarios demonstrate:
- ✅ Location filtering (Savoie, Haute-Savoie, Isère)
- ✅ Event type recognition (concerts, theater, festivals)
- ✅ Date/time handling (specific dates, weekends, months)
- ✅ Off-topic detection
- ✅ Vague query handling
- ✅ Complex multi-criteria queries
- ✅ Audience targeting (families, age groups)

The system can handle a wide range of natural language queries about cultural events in the French Alps region.
