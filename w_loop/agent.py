from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.loop_agent import LoopAgent
from google.adk.tools.tool_context import ToolContext

APP_NAME = "doc_writing_app_v3"
USER_ID = "dev_user_01"
SESSION_ID_BASE = "loop_exit_tool_session"

STATE_INITIAL_TOPIC = "initial_topic"
STATE_CURRENT_DOC = "current_document"
STATE_CRITICISM = "criticism"
COMPLETION_PHRASE = "No major issues found."

def exit_loop(tool_context: ToolContext):
  """Call this function ONLY when the critique indicates no further changes are needed, signaling the iterative process should end."""
  print(f"  [Tool Call] exit_loop triggered by {tool_context.agent_name}")
  tool_context.actions.escalate = True
  return {}

initial_writer_agent = LlmAgent(
    name="InitialWriterAgent",
    model="gemini-2.0-flash",
    include_contents='none',
    instruction=f"""You are a Creative Writing Assistant tasked with starting a story.
    Write the *first draft* of a short story (aim for 2-4 sentences).
    Base the content *only* on the topic provided below. Try to introduce a specific element (like a character, a setting detail, or a starting action) to make it engaging.
    Topic: {{initial_topic}}

    Output *only* the story/document text. Do not add introductions or explanations.
""",
    description="Writes the initial document draft based on the topic, aiming for some initial substance.",
    output_key=STATE_CURRENT_DOC
)

critic_agent_in_loop = LlmAgent(
    name="CriticAgent",
    model="gemini-2.0-flash",
    include_contents='none',
    instruction=f"""You are a Constructive Critic AI reviewing a short document draft (typically 2-6 sentences). Your goal is balanced feedback.

    **Document to Review:**
    ```
    {{current_document}}
    ```

    **Task:**
    Review the document for clarity, engagement, and basic coherence according to the initial topic (if known).

    IF you identify 1-2 *clear and actionable* ways the document could be improved to better capture the topic or enhance reader engagement (e.g., "Needs a stronger opening sentence", "Clarify the character's goal"):
    Provide these specific suggestions concisely. Output *only* the critique text.

    ELSE IF the document is coherent, addresses the topic adequately for its length, and has no glaring errors or obvious omissions:
    Respond *exactly* with the phrase "{COMPLETION_PHRASE}" and nothing else. It doesn't need to be perfect, just functionally complete for this stage. Avoid suggesting purely subjective stylistic preferences if the core is sound.

    Do not add explanations. Output only the critique OR the exact completion phrase.
""",
    description="Reviews the current draft, providing critique if clear improvements are needed, otherwise signals completion.",
    output_key=STATE_CRITICISM
)

refiner_agent_in_loop = LlmAgent(
    name="RefinerAgent",
    model="gemini-2.0-flash",
    include_contents='none',
    instruction=f"""You are a Creative Writing Assistant refining a document based on feedback OR exiting the process.
    **Current Document:**
    ```
    {{current_document}}
    ```
    **Critique/Suggestions:**
    {{criticism}}

    **Task:**
    Analyze the 'Critique/Suggestions'.
    IF the critique is *exactly* "{COMPLETION_PHRASE}":
    You MUST call the 'exit_loop' function. Do not output any text.
    ELSE (the critique contains actionable feedback):
    Carefully apply the suggestions to improve the 'Current Document'. Output *only* the refined document text.

    Do not add explanations. Either output the refined document OR call the exit_loop function.
""",
    description="Refines the document based on critique, or calls exit_loop if critique indicates completion.",
    tools=[exit_loop],
    output_key=STATE_CURRENT_DOC
)

refinement_loop = LoopAgent(
    name="RefinementLoop",
    max_iterations=5,
    sub_agents=[
        critic_agent_in_loop,
        refiner_agent_in_loop,
    ],
)

root_agent = SequentialAgent(
    name="IterativeWritingPipeline",
    description="Writes an initial document and then iteratively refines it with critique using an exit tool.",
    sub_agents=[
        initial_writer_agent,
        refinement_loop,
    ],
)
