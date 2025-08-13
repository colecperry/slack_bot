# StandupBot – Slack Daily Standup Bot (Serverless AWS Lambda + DynamoDB)

StandupBot is a serverless Slack bot that:
- Responds to the `/standup` slash command with either:
  - An instant acknowledgment if you provide text
  - An interactive modal for entering your update if you don’t
- Stores standup submissions in **DynamoDB**
- Posts a **daily summary** of all submissions to a public Slack channel
- Runs fully on **AWS Lambda + API Gateway** (no always-on server needed)

---

## 📌 Features
- **Slash command** (`/standup`) for quick daily updates
- **Interactive modal** for structured input
- **AWS Lambda + API Gateway** deployment (scales automatically, pay-per-use)
- **Persistent storage** in DynamoDB
- **Daily summaries** posted to a public Slack channel via scheduled Lambda (EventBridge)
- **Block Kit**-formatted responses for clean UI in Slack

---

## 🛠 Tech Stack
- **Slack API** (Slash Commands, Interactivity, OAuth scopes)
- **Python 3.x**
- **AWS Lambda** (serverless compute)
- **AWS API Gateway** (HTTP endpoint for Slack)
- **AWS DynamoDB** (storage for standup submissions)
- **AWS EventBridge Scheduler** (daily summary trigger)
- **boto3** (AWS SDK for Python)
- **requests** (for posting messages back to Slack)

---

## ⚙️ Prerequisites
You will need:
1. A Slack workspace where you can create and install apps  
2. An AWS account with permissions to:
   - Create and manage Lambda functions
   - Create API Gateway HTTP APIs
   - Create and read/write DynamoDB tables
   - Create EventBridge Schedules
3. Python 3.x installed locally

---

## ⚡ Setup

### 1️⃣ Create the Slack App
1. Go to [Slack API – Your Apps](https://api.slack.com/apps) → **Create New App**.
2. Select **From scratch** → Name your app (e.g., `StandupBot`) → Select your workspace.
3. Under **Slash Commands**:
   - Click **Create New Command**
   - Command: `/standup`
   - Request URL: _(leave blank for now — will add AWS API Gateway URL later)_
   - Short Description: `"Post your daily standup update"`
4. Under **Interactivity & Shortcuts**:
   - Toggle **Interactivity** ON
   - Request URL: _(leave blank for now — will add AWS API Gateway URL later)_
5. Under **OAuth & Permissions → Bot Token Scopes**, add:
    - chat:write
    - commands
    - users:read
6. Click **Install App to Workspace** and copy the **Bot User OAuth Token** (starts with `xoxb-`).
7. Copy the **Signing Secret** from **Basic Information** → **App Credentials**.

---

### 2️⃣ Create DynamoDB Table
1. Go to the [DynamoDB Console](https://console.aws.amazon.com/dynamodb/).
2. Click **Create Table**:
- Table name: `standup_logs`
- Partition key: `user_id` (String)
- Sort key: `timestamp` (String)
3. Leave other settings default and click **Create Table**.

---

### 3️⃣ Create the Lambda Function (Core Bot)
1. Go to the [AWS Lambda Console](https://console.aws.amazon.com/lambda/).
2. **Create function** → **Author from scratch**:
- Name: `slack-standup`
- Runtime: Python 3.x
3. Create or select an **execution role** with:
- `AWSLambdaBasicExecutionRole`
- `AmazonDynamoDBFullAccess` (or a restricted policy for your table)
4. In the function editor:
- Upload your bot code (`core_slack.py` and dependencies zipped).
5. Under **Configuration → Environment Variables**, add:
- SLACK_BOT_TOKEN = xoxb-your-token-here
- SLACK_SIGNING_SECRET = your-signing-secret
- DYNAMODB_TABLE = standup_logs

6. Save and Deploy.

---

### 4️⃣ Create API Gateway Endpoint
1. Go to [API Gateway Console](https://console.aws.amazon.com/apigateway/).
2. Create a new **HTTP API**.
3. Add a **POST route** (e.g., `/standup`) → integrate with your Lambda function (`slack-standup`).
4. Deploy the API and copy the **Invoke URL**.

---

### 5️⃣ Connect Slack to AWS
1. Go back to your Slack app’s **Slash Commands**:
- Update the **Request URL** to:  
  ```
  https://your-api-gateway-url/standup
  ```
2. Go to **Interactivity & Shortcuts**:
- Update the **Request URL** to the same API Gateway URL.
3. Save changes.

---

### 6️⃣ Create the Summary Lambda
1. In AWS Lambda, create another function:
- Name: `standup-summary`
- Runtime: Python 3.x
- Same execution role (must have DynamoDB + CloudWatch logs access).
2. Upload `summary_lambda.py`.
3. Add environment variables:
- SLACK_BOT_TOKEN = xoxb-your-token-here
- DYNAMODB_TABLE = standup_logs
- SUMMARY_CHANNEL_ID = C0123456789 # Slack channel ID for summary posts
- TIMEZONE = America/Los_Angeles # Optional

4. Save and Deploy.

---

### 7️⃣ Schedule Daily Summary
1. Go to [Amazon EventBridge Console](https://console.aws.amazon.com/events/).
2. Create a **Schedule**:
- Expression: e.g., `cron(0 16 ? * MON-FRI *)` for weekdays at 9 AM PT.
3. Set target as your `standup-summary` Lambda.
4. Save schedule.

---

### 8️⃣ Final Test
- Type `/standup Did project work today` in Slack → verify in DynamoDB.
- Wait for scheduled summary or run the summary Lambda manually to see the post in your Slack channel.
