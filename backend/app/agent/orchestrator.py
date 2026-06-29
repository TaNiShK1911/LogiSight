"""
Autopilot Agent Orchestrator — LangChain tool-calling agent backed by Qwen-Max.

This is the main agent definition. It is invoked by the Celery task in tasks/autopilot.py.
"""

from __future__ import annotations

import logging
import os

from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate

from app.agent.tools import (
    tool_parse_invoice_pdf,
    tool_map_charges_to_master,
    tool_detect_anomalies,
    tool_check_hitl_required,
    tool_draft_dispute_letter,
    tool_send_notifications,
    tool_write_audit_record,
)

logger = logging.getLogger(__name__)

DASHSCOPE_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

AUTOPILOT_SYSTEM_PROMPT = """\
You are LogiSight's Autopilot Agent, an expert freight invoice auditor.
Your task is to autonomously process a freight invoice from start to finish.

WORKFLOW STEPS — execute in this exact order:

1. Call tool_parse_invoice_pdf with the invoice_id to extract charge line items.
2. Call tool_map_charges_to_master with the tenant_id and the extracted line items JSON.
   - If unmapped_count > 0 in the result → call tool_check_hitl_required with
     gate_type="UNMAPPED_CHARGE" and include unmapped charge details in context_json.
   - If tool_check_hitl_required returns "PAUSED:..." → STOP and report "WORKFLOW_PAUSED".
3. Call tool_detect_anomalies with the invoice_id, mapped items, and quote_id.
   - If requires_hitl=true in the result → call tool_check_hitl_required with
     gate_type="HIGH_VALUE_ANOMALY" and include anomaly summary in context_json.
   - If tool_check_hitl_required returns "PAUSED:..." → STOP and report "WORKFLOW_PAUSED".
4. If anomalies exist (severity HIGH or MEDIUM):
   - Call tool_draft_dispute_letter with the invoice_id and anomalies JSON.
   - Call tool_check_hitl_required with gate_type="DISPUTE_APPROVAL" and the letter text in context_json.
   - If "PAUSED:..." returned → STOP and report "WORKFLOW_PAUSED".
5. Call tool_send_notifications with:
   - outcome="disputed" if anomalies were disputed (and HITL-3 was APPROVED)
   - outcome="approved" if no significant anomalies found
6. Call tool_write_audit_record with the invoice_id, workflow_id, final_status, and summary.

RULES:
- NEVER proceed past a PAUSED HITL checkpoint without explicit human approval.
- Always call tool_write_audit_record as the final step, even if the outcome is disputed.
- Be precise with amounts and reasoning — this is a financial audit context.
- If any tool returns an error, log it in the audit record and report the issue clearly.

After completing all steps, respond with a brief summary of the audit outcome.
"""


def create_autopilot_agent(
    temperature: float = 0.1,
    max_iterations: int = 25,
) -> AgentExecutor:
    """
    Create and return a configured AgentExecutor for the Autopilot workflow.

    Args:
        temperature: LLM temperature (low for determinism in audit context)
        max_iterations: Maximum agent iterations before stopping

    Returns:
        LangChain AgentExecutor ready to invoke
    """
    llm = ChatOpenAI(
        api_key=os.environ.get("DASHSCOPE_API_KEY", ""),
        base_url=DASHSCOPE_BASE_URL,
        model="qwen-max",
        temperature=temperature,
    )

    tools = [
        tool_parse_invoice_pdf,
        tool_map_charges_to_master,
        tool_detect_anomalies,
        tool_check_hitl_required,
        tool_draft_dispute_letter,
        tool_send_notifications,
        tool_write_audit_record,
    ]

    prompt = ChatPromptTemplate.from_messages([
        ("system", AUTOPILOT_SYSTEM_PROMPT),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=max_iterations,
        handle_parsing_errors=True,
        return_intermediate_steps=True,
    )

    logger.info("[ORCHESTRATOR] Autopilot agent created with Qwen-Max via DashScope")
    return executor
