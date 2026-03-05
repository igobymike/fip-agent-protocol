#!/usr/bin/env python3
"""Using templates and schedules for recurring agent messages."""

from fip import FIPClient, Template

client = FIPClient(db_path="demo.db", agent_id="agent:marcus")
client.init_db()

# Create a reusable template
template = Template(
    name="task_complete",
    injection_type="event_injection",
    priority="normal",
    delivery="text_and_tts",
    title_template="Task {task_id} Complete",
    body_template="{agent_name} finished: {description}. Duration: {duration}.",
    action_template="Review output and mark task done.",
    requires_ack=True,
    ttl_seconds=1800,
)
template_id = client.add_template(template)
print(f"Template created: id={template_id}")

# Send using the template (manually rendering for now)
title = template.title_template.format(task_id="TSK-142")
body = template.body_template.format(
    agent_name="coding-worker-01",
    description="API endpoint implementation",
    duration="47 minutes",
)
result = client.send(
    target="agent:marcus",
    event_type="task.complete",
    title=title,
    body=body,
    priority=template.priority,
    requires_ack=template.requires_ack,
)
print(f"Sent: {result}")
