# RCAccelerator

A Chainlit-based chatbot with RAG (Retrieval-Augmented Generation) capabilities for accelerating Root Cause Analysis (RCA) in Continuous Integration (CI) environments.

## Overview

RCAccelerator is an interactive AI assistant designed to assist engineering teams in identifying, analyzing, and resolving CI failures more efficiently. Built on top of [Chainlit](https://www.chainlit.io/), it leverages LLMs and vector search to combine conversational intelligence with deep contextual recall of past incidents, bugs, and system knowledge.

## Running the App

1. (Optional) [Manually install PDM](https://pdm-project.org/en/latest/#installation) or go to step 2 directly.

2. Install dependencies (which also takes care of installing PDM if needed):
   ```bash
   make install-deps
   ```

3. Configure your environment:
   - Create a `.env` file or export the necessary environment variables.

4. Start the Chainlit app:
   ```bash
   pdm run chainlit run app.py
   ```

   Replace `app.py` with your actual entry point filename.
