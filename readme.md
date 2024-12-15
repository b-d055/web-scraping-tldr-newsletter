# Bright Data Newsletter Demo

This project demonstrates how to use the Bright Data API to fetch articles from Reddit and Google News, summarize them using OpenAI, and send the results via email using Mailgun.

Originally written for the [Bright Data Web Scraping Challenge](https://dev.to/t/brightdatachallenge). My submission [here](https://dev.to/b-d055/using-bright-data-and-openai-to-auto-generate-tldr-style-newsletters-42cl).

## Prerequisites

- Python 3.7 or higher
- A Mailgun account and API key
- A Bright Data account and API key
- An OpenAI account and API key

## Setup

1. Clone the repository:

```sh
git clone https://github.com/yourusername/bright-data-api-demo.git
cd bright-data-api-demo
```

2. Create a virtual environment and activate it:

```sh
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

3. Install the required packages:

```sh
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory of the project and add your API keys:

```env
MAILGUN_API_KEY=your-mailgun-api-key
MAILGUN_DOMAIN=your-mailgun-domain
TO_EMAIL=recipient@example.com
OPENAI_API_KEY=your-openai-api-key
BRIGHTDATA_API_KEY=your-brightdata-api-key
```

5. Ensure you have a valid `template.html` file in the root directory for formatting the email content.

## Usage

To run the script and generate the newsletter, execute:

```sh
python main.py
```