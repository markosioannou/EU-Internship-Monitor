# EurOdyssey Traineeship Monitor

Automatically monitors the EurOdyssey website for new traineeship opportunities and sends Telegram notifications.

## 🚀 GitHub Actions Setup

This repository runs automatically every 2 hours using GitHub Actions to check for new traineeships.

### Prerequisites

1. **Telegram Bot**: Create via [@BotFather](https://t.me/BotFather)
2. **Chat ID**: Get from [@userinfobot](https://t.me/userinfobot)
3. **GitHub Account**: To host and run the scripts

### Setup Instructions

#### 1. Fork/Create Repository
- Fork this repository or create a new one
- Upload these files:
  - `eurodyssey_monitor_github.py` (main script)
  - `.github/workflows/eurodyssey-monitor.yml` (GitHub Actions workflow)

#### 2. Configure Secrets
Go to your repository → Settings → Secrets and variables → Actions

Add these **Repository Secrets**:
- `TELEGRAM_BOT_TOKEN`: Your bot token from @BotFather
- `TELEGRAM_CHAT_ID`: Your personal chat ID from @userinfobot

#### 3. Enable GitHub Actions
- Go to the **Actions** tab in your repository
- If prompted, enable GitHub Actions for your repository
- The workflow will start running automatically

#### 4. Manual Test (Optional)
- Go to Actions → "EurOdyssey Traineeship Monitor"
- Click "Run workflow" to test immediately

### 📊 Data Storage

- **CSV File**: `eurodyssey_traineeships.csv` stores all discovered traineeships
- **Automatic Updates**: The workflow commits new data back to the repository
- **Historical Data**: Complete history of all traineeships with discovery dates

### 🔄 Schedule

- **Frequency**: Every 2 hours
- **Time Zone**: UTC (GitHub Actions default)
- **Customization**: Edit the cron expression in the workflow file

```yaml
schedule:
  - cron: '0 */2 * * *'  # Every 2 hours
  # - cron: '0 */6 * * *'  # Every 6 hours
  # - cron: '0 9,17 * * *'  # 9 AM and 5 PM UTC daily
```

### 📱 Notification Format

When new traineeships are found, you'll receive:

```
🚨 1 New EurOdyssey Traineeship(s) Found!

*1. English Teachers and Project support*
📋 Area: Education and Pedagogy  
📍 Region: Catalonia, Spain
📅 Period: 01/08/2025 - 31/12/2025
⏰ Deadline: 24/06/2025
🔢 Reference: N147586/20/CATALUNYA
🔗 View Details
```

### 🛠️ Troubleshooting

#### No Notifications Received
1. Check if GitHub Actions are running (Actions tab)
2. Verify Telegram secrets are set correctly
3. Make sure you've messaged your bot first (`/start`)

#### Workflow Failures
1. Check the Actions tab for error logs
2. Common issues:
   - Invalid Telegram credentials
   - Website structure changes
   - Rate limiting

#### CSV Not Updating
1. Ensure the repository has write permissions
2. Check if the workflow has permission to commit files

### 🔧 Customization

#### Change Monitoring URL
Edit `TRAINEESHIP_URL` in `eurodyssey_monitor_github.py`:

```python
TRAINEESHIP_URL = "https://eurodyssey.aer.eu/traineeships/?your-filters-here"
```

#### Modify Notification Content
Update the `send_telegram_alert()` method to customize message format.

#### Add Email Notifications
You can extend the script to also send emails using GitHub's email integration.

### ⚠️ Limitations

#### GitHub Actions Limits
- **Public repos**: Unlimited minutes
- **Private repos**: 2,000 minutes/month free
- **Storage**: 500MB for Actions artifacts

#### Rate Limiting
- Script includes 2-second delays between requests
- Monitors respectfully to avoid overwhelming the server

### 🆘 Support

#### Common Cron Expressions
```yaml
'0 */1 * * *'   # Every hour
'0 */3 * * *'   # Every 3 hours  
'0 9 * * *'     # Daily at 9 AM UTC
'0 9 * * 1-5'   # Weekdays at 9 AM UTC
```

#### Getting Help
1. Check the **Issues** tab for common problems
2. Review **Actions** logs for detailed error messages
3. Test your Telegram setup manually first

### 📈 Alternative Hosting Options

If GitHub Actions limitations are a concern:

1. **Heroku**: Free tier with 550 hours/month
2. **Railway**: Simple deployment with generous free tier
3. **PythonAnywhere**: Free tier perfect for scheduled tasks
4. **Google Cloud Run**: Pay-per-use, very cheap for this use case
5. **AWS Lambda**: Event-driven, minimal costs

### 🎯 Expected Behavior

1. **First Run**: Discovers all current traineeships, saves to CSV, no notifications
2. **Subsequent Runs**: Only notifies about genuinely new traineeships
3. **Data Persistence**: CSV accumulates historical data over time
4. **Reliability**: Handles errors gracefully and continues monitoring

The system is designed to be "set and forget" - once configured, it will reliably monitor and notify you of new opportunities!
