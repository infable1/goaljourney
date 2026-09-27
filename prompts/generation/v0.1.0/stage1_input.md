# Task: write the model INPUT for one training example

Operation: {{operation}}
Today's date for the example: {{today}}

Scenario seed (a compact description of the user situation):
{{scenario_json}}

Write the request object the GoalJourney app would send to the navigator model for this operation, at the moment described by the scenario. Include only the context this operation needs:
{{operation_input_hint}}

Rules:
- Conform exactly to the JSON Schema below. Set "operation" to "{{operation}}" and "today" to "{{today}}".
- The user's own messages go in "conversation" (role "user"); write them in {{input_language_hint}}.
- Do not solve the task and do not hint at the ideal answer inside the input.
- Keep known facts consistent with the scenario; leave unknowns unknown.

JSON Schema (input_context):
{{input_schema}}
