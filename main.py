import os
import json
import requests
import schedule

from dotenv import load_dotenv
from openai import OpenAI
import time
from datetime import datetime, timedelta

load_dotenv()

MAILGUN_DOMAIN = os.environ.get('MAILGUN_DOMAIN')
MAILGUN_API_KEY = os.environ.get('MAILGUN_API_KEY')
TO_EMAIL = os.environ.get('TO_EMAIL')
BRIGHTDATA_API_KEY = os.environ.get('BRIGHTDATA_API_KEY')

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),  # This is the default and can be omitted
)

def get_reddit_articles(subreddit):
	url = "https://api.brightdata.com/datasets/v3/trigger?dataset_id=gd_lvz8ah06191smkebj4&include_errors=true&type=discover_new&discover_by=subreddit_url&limit_per_input=10"

	payload = json.dumps([
	{
		"url": f"https://www.reddit.com/r/{subreddit}",
		"sort_by": "Hot"
	}
	])
	headers = {
		'Content-Type': 'application/json',
		'Authorization': f'Bearer {BRIGHTDATA_API_KEY}'
	}

	response = requests.request("POST", url, headers=headers, data=payload)

	return response.json()

def get_google_news_articles(titles):
	url = "https://api.brightdata.com/datasets/v3/trigger?dataset_id=gd_lnsxoxzi1omrwnka5r&include_errors=true&limit_multiple_results=10"
	
	payload = []

	for title in titles:
		payload.append({
			"url": "https://news.google.com/",
			"keyword": title,
			"country": "",
			"language": ""
		})
	payload = json.dumps(payload)

	headers = {
	'Content-Type': 'application/json',
	'Authorization': f'Bearer {BRIGHTDATA_API_KEY}'
	}

	response = requests.request("POST", url, headers=headers, data=payload)
	return response.json()


def get_snapshot_results(snapshot_id):
	url = f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}?format=json"

	payload = {}
	headers = {
		'Authorization': f'Bearer {BRIGHTDATA_API_KEY}'
	}

	response = requests.request("GET", url, headers=headers, data=payload)

	return response.json()


def send_simple_message():
  	return requests.post(
  		f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
  		auth=("api", MAILGUN_API_KEY),
  		data={"from": f"Excited User <mailgun@{MAILGUN_DOMAIN}>",
  			"to": [os.environ.get('TO_EMAIL')],
  			"subject": "Hello",
  			"html": ""})

def send_html_message(html):
	return requests.post(
		f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
		auth=("api", MAILGUN_API_KEY),
		data={"from": f"Newsletter <mailgun@{MAILGUN_DOMAIN}>",
			"to": [os.environ.get('TO_EMAIL')],
			"subject": "Hello",
			"html": html})

def get_article_summary(comments, article_title):
	# Prompt definitely could be improved
	chat_completion = client.chat.completions.create(
		messages=[
			{
				"role": "user",
				"content": f"Article title:\n{article_title}\n\nComments:{comments}\n---\nGiven the above comments and new article, write a summary of the reddit comments. Do not mention reddit or the specific comments in the summary, just summarize the general reaction in 2 or 3 sentences.",
			}
		],
		model="gpt-4o-mini",
	)
	result = chat_completion.choices[0].message.content
	return result

def get_snapshot(snapshot_id):
	snapshot_result = get_snapshot_results(snapshot_id)
	snapshot_status = snapshot_result.get('status', 'ready') if isinstance(snapshot_result, dict) else 'ready'
	print(snapshot_result)
	while snapshot_status in ['running', 'building']:
		time.sleep(10)
		snapshot_result = get_snapshot_results(snapshot_id)
		snapshot_status = snapshot_result.get('status', 'ready') if isinstance(snapshot_result, dict) else 'ready'
		print(snapshot_result)
	return snapshot_result

def get_reddit_snapshot(snapshot_id, folder_name="data"):
	result = get_snapshot(snapshot_id)
	save_results_to_json(result, 'reddit_snapshot', folder_name)
	return result

def get_google_snapshot(snapshot_id, folder_name="data"):
	result = get_snapshot(snapshot_id)
	save_results_to_json(result, 'google_snapshot', folder_name)
	return get_snapshot(snapshot_id)

def format_article_to_html(articles):
	html_template = open('template.html', 'r').read()
	# that are more elegant ways to do this, but this works
	chat_completion = client.chat.completions.create(
		messages=[
			{
				"role": "user",
				"content": f"Email template:\n{html_template}\n\nArticles w/summary:{articles}\n---\nGiven the above email template and articles with summary, format the articles into the email template. Replace all brackets with content from articles/comments. Be sure to include the article links in href. Do not respond with anything other than raw HTML, do not enclose HTML in quotes.",
			}
		],
		model="gpt-4o-mini",
	)
	result = chat_completion.choices[0].message.content
	return result

def save_results_to_json(results, name, folder_name):
	# use timestamp to create unique file name
	timestamp = time.strftime("%Y%m%d-%H%M%S")
	if not os.path.exists(folder_name):
		os.makedirs(folder_name)
	with open(f'{folder_name}/{name}-{timestamp}.json', 'w') as f:
		json.dump(results, f)

def save_results_to_html(results, name, folder_name):
	# use timestamp to create unique file name
	timestamp = time.strftime("%Y%m%d-%H%M%S")
	if not os.path.exists(folder_name):
		os.makedirs(folder_name)
	with open(f'{folder_name}/{name}-{timestamp}.html', 'w') as f:
		f.write(results)

def get_newsletter(subreddit="news"):
	print(f"Getting reddit articles for '{subreddit}'")
	reddit_response = get_reddit_articles(subreddit)
	print(f"Reddit response: {reddit_response}")
	snapshot_id = reddit_response.get('snapshot_id')

	if not snapshot_id:
		print("No snapshot id found")
		return
	
	reddit_posts = get_reddit_snapshot(snapshot_id)
	titles = [post.get('title') for post in reddit_posts]
	print(f"Titles: {titles}")

	google_news_response = get_google_news_articles(titles)
	google_snapshot_id = google_news_response.get('snapshot_id')

	if not google_snapshot_id:
		print("No google snapshot id found")
		return
	
	google_snapshot_result = get_google_snapshot(google_snapshot_id)
	
	combined_results = []
	for post in reddit_posts:
		articles = list(filter(lambda x: x.get('keyword') == post.get('title'), google_snapshot_result))
		# we only want fresh articles
		last_week = datetime.now() - timedelta(days=3)
		articles = list(filter(lambda x: x.get('date') >= last_week.isoformat(), articles))
		media_links = [article.get('url') for article in articles]
		media_links.insert(0, post.get('url'))
		comments = post.get('comments')
		summary = get_article_summary(comments, post.get('title'))
		combined_results.append({
			'title': post.get('title'),
			'summary': summary,
			'outlets': media_links
		})
	
	save_results_to_json(combined_results, 'combined_results', 'data')
	# combined_results = json.load(open('data/combined_results-20241213-150824.json', 'r'))

	result = format_article_to_html(combined_results)
	result = result.strip('`').strip('"').strip("'").strip('html')
	save_results_to_html(result, 'formatted_results', 'newsletter')

	email_response = send_html_message(result)
	print(f"Email response status: {email_response.status_code}")
	print(f"Email response text: {email_response.text}")

def get_technews_newsletter():
	get_newsletter("technews")

if __name__ == "__main__":
	schedule.every().day.at("8:30").do(get_technews_newsletter)

	while True:
		schedule.run_pending()
		time.sleep(1)










