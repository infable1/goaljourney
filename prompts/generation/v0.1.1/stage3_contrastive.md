# Task: write a REJECTED output for preference training

Operation: {{operation}}
Failure mode(s) to demonstrate: {{failure_modes}}
Definitions:
{{failure_mode_definitions}}

Input:
{{input_json}}

Ideal output (for reference — do NOT copy it):
{{expected_json}}

Write a plausible but clearly worse output that exhibits exactly the listed failure mode(s) and is otherwise realistic. It MUST still conform to the JSON Schema below (the failure is behavioural, not a formatting error). Reply with a JSON object: {"output": <the rejected output>, "critique": "<one or two sentences explaining what is wrong and why it hurts the user>"}.

JSON Schema:
{{output_schema}}
