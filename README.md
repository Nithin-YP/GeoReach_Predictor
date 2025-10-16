# GeoReach Predictor 🎯

GeoReach Predictor is a Django-based interactive GIS platform that helps entrepreneurs visualize, simulate, and predict the market reach and success probability of a new product before launch. It combines demographic, expenditure, interest, and employment data with predictive analytics to simulate market success across geographic clusters.

## ✨ Features

- **🔐 User Authentication**: Role-based access control (Admin/Entrepreneur)
- **📊 ML-Powered Predictions**: RandomForest + KMeans clustering for market analysis
- **🗺️ Geographic Insights**: State-wise market reach predictions
- **📱 Responsive UI**: Modern Bootstrap 5 interface with icons
- **👥 User Management**: Admin interface for managing users and datasets
- **🔄 Graceful Fallbacks**: Works with or without ML libraries installed
- **🎨 Professional Design**: Clean, intuitive dashboard interface

## 🚀 Quick Start

### Prerequisites
- Python 3.8+ 
- Virtual Environment (recommended)
- Git

### 1. Clone & Setup
```bash
git clone https://github.com/Strange-0007/GeoReach_Predictor.git
cd GeoReach_Predictor

# Create virtual environment
python -m venv .env

# Activate virtual environment
# Windows:
.\.env\Scripts\activate
# macOS/Linux:
source .env/bin/activate
```

### 2. Install Dependencies
```bash
# Install all dependencies (including ML libraries)
pip install -r requirements.txt

# OR install minimal Django-only setup
pip install Django>=5.2.7 django-environ>=0.11.2
```

### 3. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your settings (optional for development)
```

### 4. Database Setup
```bash
# Apply migrations
python manage.py migrate
cd scripts
python data_loading.py

# Create superuser (admin)
python manage.py create_admin
# Default credentials: admin / adminpassword
```

### 5. Train ML Models (Optional)
```bash
# Train ML models for predictions (requires ML libraries)
python manage.py train_models
```

### 6. Run Development Server
```bash
python manage.py runserver
```

🎉 **Access the application at: http://127.0.0.1:8000**

## 🔧 VS Code Setup & Configuration

This project includes optimized VS Code configurations for the best development experience.

### Auto-Configuration Files

The project includes these VS Code configuration files:

#### `.vscode/settings.json`
```json
{
    "python.defaultInterpreterPath": "../.env/Scripts/python.exe",
    "python.pythonPath": "../.env/Scripts/python.exe",
    "python.terminal.activateEnvironment": true,
    "python.analysis.typeCheckingMode": "basic",
    "html.validate.scripts": false,
    "emmet.includeLanguages": {
        "django-html": "html"
    }
}
```

#### `pyrightconfig.json` 
```json
{
    "venvPath": "../",
    "venv": ".env",
    "pythonVersion": "3.13",
    "typeCheckingMode": "basic",
    "extraPaths": ["./core", "./georeach_predictor"]
}
```

### VS Code Extensions (Recommended)

Install these extensions for the best experience:

```bash
# Essential Python & Django
code --install-extension ms-python.python
code --install-extension ms-python.pylint
code --install-extension batisteo.vscode-django

# Web Development
code --install-extension ms-vscode.vscode-html-css-support
code --install-extension bradlc.vscode-tailwindcss
code --install-extension formulahendry.auto-rename-tag

# Git & Productivity
code --install-extension eamodio.gitlens
code --install-extension ms-vscode.vscode-json
```

### Automatic Environment Detection

1. **Open project in VS Code**:
   ```bash
   code .
   ```

2. **Select Python Interpreter**:
   - Press `Ctrl+Shift+P` (Windows) or `Cmd+Shift+P` (Mac)
   - Type "Python: Select Interpreter"
   - Choose: `.\.env\Scripts\python.exe`

3. **VS Code will automatically**:
   - Detect Django project structure
   - Enable Django template syntax highlighting
   - Configure proper linting and formatting
   - Set up integrated terminal with virtual environment

### Troubleshooting VS Code Issues

**Import Errors in Problems Panel?**
- These are expected if ML libraries aren't installed
- Application works perfectly with dummy data fallback
- Install ML libraries to remove warnings: `pip install pandas numpy scikit-learn joblib`

**Django imports not recognized?**
- Ensure virtual environment is activated
- Check Python interpreter path in VS Code
- Restart VS Code after changing interpreter

## 📋 Usage Guide

### Default Login Credentials
- **Admin**: `admin` / `adminpassword`
- **Register new entrepreneur account** via the registration form

### Admin Dashboard
- **User Management**: Block/unblock users, manage accounts
- **Dataset Management**: View and manage ML datasets
- **System Status**: Monitor ML models and application health

### Entrepreneur Dashboard
- **Create Predictions**: Enter product details for market analysis
- **View Results**: See predicted reach percentage and success probability
- **History**: Track past predictions and compare results

## 🗂️ Project Structure

```
GeoReach_Predictor/
├── 📁 core/                          # Main Django app
│   ├── 📁 management/commands/        # Custom management commands
│   ├── 📁 migrations/                 # Database migrations
│   ├── 📁 models_ml/                  # Trained ML models storage
│   ├── 📁 templates/core/             # HTML templates
│   ├── 📁 templatetags/               # Custom template filters
│   ├── 📄 admin.py                    # Django admin configuration
│   ├── 📄 forms.py                    # Django forms
│   ├── 📄 models.py                   # Database models
│   ├── 📄 ml_pipeline.py              # ML pipeline & predictions
│   ├── 📄 urls.py                     # App URL configuration
│   └── 📄 views.py                    # View logic
├── 📁 datasets/                       # CSV datasets for ML training
├── 📁 docs/                          # Project documentation
├── 📁 georeach_predictor/             # Django project settings
├── 📁 static/                         # Static files (CSS, JS, images)
├── 📁 templates/                      # Base templates
├── 📁 .vscode/                        # VS Code configuration
├── 📄 .env.example                    # Environment variables template
├── 📄 .gitignore                      # Git ignore rules
├── 📄 db.sqlite3                      # SQLite database (development)
├── 📄 manage.py                       # Django management script
├── 📄 pyrightconfig.json              # Python type checking config
├── 📄 requirements.txt                # Python dependencies
└── 📄 README.md                       # This file
```

## 🧪 Development Commands

```bash
# Database operations
python manage.py makemigrations          # Create new migrations
python manage.py migrate                 # Apply migrations
python manage.py createsuperuser         # Create admin user manually

# ML & Data
python manage.py train_models           # Train ML models
python manage.py create_admin           # Create default admin

# Development
python manage.py runserver              # Start development server
python manage.py runserver 0.0.0.0:8000 # Run on all interfaces
python manage.py check                  # Check for issues
python manage.py collectstatic          # Collect static files

# Testing
python manage.py test                   # Run tests
```

## 🔧 Configuration Options

### Environment Variables (.env)
```bash
# Django Core
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=sqlite:///db.sqlite3
# DATABASE_URL=postgresql://user:pass@localhost/dbname  # For PostgreSQL

# Admin Credentials
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=change-this-password

# Security (Production)
SECURE_SSL_REDIRECT=False
SECURE_BROWSER_XSS_FILTER=True
SECURE_CONTENT_TYPE_NOSNIFF=True
```

### Database Options
- **Development**: SQLite (default, no setup required)
- **Production**: PostgreSQL (recommended)
  ```bash
  pip install dj-database-url psycopg2
  # Set DATABASE_URL=postgresql://user:pass@host:port/dbname
  ```

## 🚀 Deployment

### Production Checklist
- [ ] Set `DEBUG=False` in environment
- [ ] Configure proper `SECRET_KEY`
- [ ] Set up PostgreSQL database
- [ ] Configure static files serving
- [ ] Set up HTTPS (SSL certificates)
- [ ] Configure security headers
- [ ] Set up monitoring and logging

### Quick Deploy (Heroku Example)
```bash
# Add Procfile
echo "web: python manage.py migrate && python manage.py collectstatic --noinput && python manage.py runserver 0.0.0.0:\$PORT" > Procfile

# Deploy to Heroku
heroku create your-app-name
heroku addons:create heroku-postgresql:hobby-dev
heroku config:set SECRET_KEY=your-production-secret-key
heroku config:set DEBUG=False
git push heroku main
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

**Having issues?**
- Check the [Issues](https://github.com/Strange-0007/GeoReach_Predictor/issues) page
- Create a new issue with detailed description
- Include error messages and environment details

**Common Issues:**
- **Import errors**: Install dependencies with `pip install -r requirements.txt`
- **VS Code not detecting environment**: Select correct Python interpreter
- **Permission errors**: Run commands from activated virtual environment
- **Database errors**: Run `python manage.py migrate`

---

**Built with ❤️ using Django, Bootstrap, and Machine Learning**

*GeoReach Predictor - Empowering entrepreneurs with data-driven market insights* 🚀