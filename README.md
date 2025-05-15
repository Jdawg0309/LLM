# LLMScribe - AI-Powered Text Editor

An intelligent text editing system that leverages Local Language Models (LLM) to help users improve their writing.

## Features

- **User Tiers**
  - Free Users: Edit texts up to 20 words with cooldown period
  - Paid Users: Unlimited text length with token system
  - Super Users: Manage user applications and handle disputes

- **Core Functionality**
  - Text input via typing or file upload
  - LLM-powered grammar and spelling correction
  - Interactive correction system with user approval
  - Blacklist word filtering
  - Self-correction options
  - Token-based economy

- **Collaborative Features**
  - Text file sharing between paid users
  - Collaboration invitations
  - Dispute resolution system
  - User statistics tracking

- **Security**
  - Secure user authentication
  - Token management system
  - Protected API integration
  - User activity monitoring

## Prerequisites

- Python 3.10 or higher
- Local LLM setup (Hugging Face/Ollama)
- MySQL Database

## Setup Instructions

1. Clone and navigate to the project:
```sh
git clone https://github.com/Jdawg0309/LLM.git
cd LLM
```

2. Create and activate a virtual environment:
```sh
python3 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:
```sh
pip install -r requirements.txt
```

4. Configure environment variables in `.env`

## Running the Application

1. Activate virtual environment:
```sh
source .venv/bin/activate
```

2. Start the Flask server:
```sh
python backend/app.py
```

3. Access the application at `http://localhost:5000`

## Team Members

- Sean Jenkins
- Junaet Mahbub
- Adama Faye
- Rajiv Seeram
- Nischal Thapa

# Phase I: Software Requirements Specification Report

You can view our SRS Report here: [Software Requirements Specification Report](documentation/teamS_1stphasereport.pdf)

# Phase II: Design Report

You can view our Design Report here: [Design Report](documentation/teamS_2ndphasereport.pdf)

## License

This project is licensed under the MIT License - see the LICENSE file for details.


@workspace Make it so that instead of the system preventing the user from typing past 20 words, make it so that users still can type in 20 words, However a warning message will pop up stating "Free users are limited to 20 words. If you submit more than 20 words, you will be logged out immediately and a 3 minute cooldown will be put on you" or something like that. And if the user decides to try more than 20 words anyways, they get immediately logged out and can't sign in for 3 minutes