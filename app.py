from flask import Flask, request, render_template
from markupsafe import escape
import pickle

import language_tool_python
from better_profanity import profanity
import requests

vector = pickle.load(open("vectorizer.pk1", 'rb'))
model = pickle.load(open("finalized_model.pk1", 'rb'))


tool = language_tool_python.LanguageTool('en-US')
profanity.load_censor_words()
# Pre-warm language tool to reduce first-request delay
_ = tool.check("This is a warmup sentence.")

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/prediction", methods=['GET', 'POST'])
def prediction():
    if request.method == "POST":
        news = str(request.form['news'])
        print(news)

        # Fake news prediction
        predict = model.predict(vector.transform([news]))[0]
        print(predict)

        # Grammar/Correctness check
        matches = tool.check(news)
        grammar_issues = len(matches)
        grammar_feedback = "No major issues found." if grammar_issues == 0 else f"{grammar_issues} issue(s) detected."

        # Credibility check using Google Fact Check Tools API
        api_url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
        api_key = "AIzaSyB-nGz-8a1I5l5Mi6scApdFh9X2b4UGjxc"  # Replace with your API key
        credibility_feedback = "No real-time fact-check found."
        try:
            params = {
                "query": news,
                "key": api_key,
                "languageCode": "en-US"
            }
            response = requests.get(api_url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                claims = data.get("claims", [])
                if claims:
                    claim = claims[0]
                    text = claim.get("text", "")
                    claim_reviews = claim.get("claimReview", [])
                    if claim_reviews:
                        review = claim_reviews[0]
                        publisher = review.get("publisher", {}).get("name", "Unknown publisher")
                        title = review.get("title", "Fact Check")
                        url = review.get("url", "")
                        verdict = review.get("textualRating", "No verdict")
                        credibility_feedback = f"Fact-checked by {publisher}: {verdict}. <a href='{url}' target='_blank'>{title}</a>"
                    else:
                        credibility_feedback = "No detailed fact-check review found, but claim exists."
                else:
                    credibility_feedback = "No real-time fact-check found."
            else:
                credibility_feedback = "Fact check API error."
        except Exception as e:
            credibility_feedback = "Fact check unavailable."

        # Abuse detection
        is_abusive = profanity.contains_profanity(news)
        abuse_feedback = "Abusive language detected!" if is_abusive else "No abusive language detected."

        return render_template(
            "prediction.html",
            prediction_text=f"News headline is {predict}",
            grammar_feedback=grammar_feedback,
            credibility_feedback=credibility_feedback,
            abuse_feedback=abuse_feedback
        )
    else:
        return render_template("prediction.html")
        
        
if __name__ == '__main__':
    app.run(debug=True)