# NovaMart multi-agent customer support

A self-grading exercise based on Udacity's [Multi-Agent E-commerce RAG starter](https://github.com/udacity/cd14764-aws-agentic-c3-classroom/tree/main/project/starter). It uses Strands agents and Amazon Bedrock AgentCore to route synthetic customer requests, query three policy knowledge bases, and process mock returns.

This repository is for learning and has not been submitted for grading. It contains Udacity starter material; see [UDACITY-LICENSE.md](UDACITY-LICENSE.md) and [UDACITY-STARTER-README.md](UDACITY-STARTER-README.md) for its terms and original instructions.

## Architecture

```text
Customer request -> Orchestrator (Haiku 4.5)
  -> Inventory (DynamoDB) -> Refund (return-window checks)
  -> Policy (Sonnet 4.5) -> Returns / Shipping / Warranty KBs in parallel
  -> Communication -> customer response
Shared workflow state: DynamoDB; safety: Bedrock Guardrails;
runtime: AgentCore; logs and traces: CloudWatch / X-Ray.
```

The diagram shows available routes; the orchestrator chooses which workers to call. Return checks use a 30-day Standard or 60-day Premium window and a conditional order update. A repeated return reuses its reference.

## Setup

1. Use Python 3.12, Node.js 20+, `uv`, and AWS credentials for `us-east-1`. Provisioning and model calls can incur charges. Configure a restricted sandbox account and monitor its budget.
2. Install `pip install -r requirements.txt` and `npm install -g @aws/agentcore@0.30.0`. Run `npm ci --prefix agentcore/cdk`.
3. Copy `.env.example` to `.env`; copy `agentcore/agentcore.example.json` to `agentcore/agentcore.json` and `agentcore/aws-targets.example.json` to `agentcore/aws-targets.json`. These local files are ignored by Git.
4. Deploy `infrastructure/starter_stack.yaml` as CloudFormation stack `udacity-agentcore` with `CAPABILITY_NAMED_IAM`, then run `python infrastructure/seed_data.py`. Create and sync the three Bedrock knowledge bases using the stack's S3 Vectors indexes and Titan Text Embeddings V2; populate their IDs in `.env`. The detailed console procedure is in the original starter README.
5. Run `python src/agent_orchestrator.py deploy`, save its runtime ARN and guardrail ID/version to `.env`, and invoke with `python src/agent_orchestrator.py invoke "What is the return policy?"`.

## Self-grading

Run `python tests/test_agent.py task2`, then `task3`, `task4`, `task5`, `task6`, or `all` after provisioning. The provided suite checks configuration as well as some live retrieval; a passing score alone does not prove all security or customer-facing behavior. Run `python src/agent_orchestrator.py test` for the three live scenarios and inspect the X-Ray service map. On Windows, set `PYTHONIOENCODING=utf-8` if the test runner cannot print Unicode.

Recorded on November 6, 2026 in the Udacity sandbox: the unchanged full grading script reported **120/120**; all three KB ingestion jobs completed and returned passages. The local scenario run initiated a mock return, answered a Premium policy question, and calculated **$134.96** for five items at $29.99 with a 10% discount. A wrong-customer order lookup returned not found. A guardrail input test allowed discount arithmetic and blocked a negotiation request. The X-Ray API showed a connected graph including the orchestrator, workers, and three knowledge bases; a console screenshot was not captured.

For local logic checks, run `python -m unittest discover -s tests -p test_refunds.py` and `python -m unittest discover -s tests -p test_return_rules.py`.

## Security and limitations

Use synthetic data only. IAM-authenticated runtime access is not customer authentication: the supplied customer ID must be bound to a verified identity before using real customer data. The starter's observability and session behavior are educational and need a privacy and concurrency review before production. Routing and arithmetic rely on model instructions and can vary: one initial hosted invocation rounded incorrectly and bypassed a required tool; a later local retest passed after prompt changes, but this is not a deterministic guarantee. The AgentCore Memory resource configuration alone does not demonstrate that the application writes and retrieves conversation history. Never commit credentials, `.env`, deployment state, or account-specific runtime configuration.
