# CollegeMate - BMIT Solapur AI Assistant

CollegeMate is an AI-powered assistant for Brahmdevdada Mane Institute of Technology, Solapur. It helps students with admissions inquiries, course information, and campus facilities.

## Features

- AI-powered chat interface
- Voice interaction support
- Course information and admission details
- Campus facilities information
- Admin dashboard for monitoring interactions
- User registration and authentication
- Document management system

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- OpenAI API key
- SMTP server credentials (for email notifications)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/collegemate.git
cd collegemate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Update the following variables in `.env`:
     - `SECRET_KEY`: Your Flask secret key
     - `OPENAI_API_KEY`: Your OpenAI API key
     - `SMTP_USERNAME`: Your email address
     - `SMTP_PASSWORD`: Your email app password
     - `COLLEGE_EMAIL`: College contact email

## Running the Application

1. Initialize the database:
```bash
python app.py
```

2. Access the application:
   - Main interface: http://localhost:5000
   - Admin panel: http://localhost:5000/admin
   - Default admin credentials:
     - Username: admin
     - Password: Bmit@24

## Features

### User Interface
- Modern, responsive design
- Real-time chat with AI assistant
- Voice interaction support
- Course and facility information display

### Admin Panel
- Monitor chat interactions
- View visitor statistics
- Manage admission applications
- Update college information
- Upload and manage documents

### Security
- User authentication
- Secure password hashing
- Protected admin routes
- Session management

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Course Information

- BBA (Bachelor of Business Administration): ₹45,000 per year, 3 years
- BCA (Bachelor of Computer Applications): ₹42,000 per year, 3 years
- MBA (Master of Business Administration): ₹75,000 per year, 2 years
- MCA (Master of Computer Applications): ₹72,000 per year, 2 years

## Technical Details

- Backend: Flask (Python)
- Frontend: HTML, CSS, JavaScript
- AI: GPT-4
- Database: SQLite
- Text-to-Speech: Edge TTS
- Speech Recognition: Web Speech API

## About BMIT Solapur

Bharati Vidyapeeth Institute of Management & Information Technology, Solapur is a premier educational institution offering quality education in management and IT fields. Located at Solapur - Pune National Highway, Telangwadi Fhata, Kasegaon, Maharashtra 413304.

### Departments
- Computer Science
- Management
- Information Technology
- Commerce

### Campus Facilities
- Library
- Computer Labs
- Seminar Hall
- Canteen
- Sports Ground
- Wi-Fi Campus 