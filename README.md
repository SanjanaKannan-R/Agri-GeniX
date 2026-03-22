# Agri Genix 🌾

Empowering Farmers, Reducing Waste, Enhancing Profits through Digital Connectivity.

Agri Genix is a web-based platform designed to bridge the digital gap in the agricultural sector. By connecting farmers directly with buyers and providing real-time data on warehouse (godown) availability, the platform minimizes post-harvest losses and ensures farmers get the best value for their produce.


## The Problem
Every year, a significant percentage of crops go to waste due to a lack of immediate market access and inadequate information regarding storage facilities. Farmers often struggle to find buyers or don't know where the nearest available warehouse is located.


## ✅ The Solution: Agri Genix
Direct Marketplace: A digital platform for farmers to list crops and buyers to browse them.

Smart Storage: Integration with government APIs (data.gov.in) to locate nearby godowns.

IVR System: Voice-based interaction for farmers to check storage and crop status without needing a smartphone or internet.

SMS Gateway: Real-time text alerts for buyer interest, OTP verification, and storage updates.
## ✨Features
Secure Authentication: User registration via mobile/email with OTP verification via SMS.

Crop Management: Farmers can easily upload details including crop name, quantity, and location.

Smart Storage Locator: Fetches nearby godown/warehouse data via APIs to offer storage options when immediate selling is not possible.

Direct Buyer Marketplace: Buyers can search, view listings, and contact farmers directly, removing unnecessary middlemen.

IVR (Interactive Voice Response): Allows farmers to interact with the system via phone calls to get updates on crop prices or storage availability.

Automated SMS Alerts: Instant notifications for buyer inquiries, storage confirmations, and platform updates.

## 🛠️ Tech Stack
Frontend : HTML5, CSS3

Backend	: Python (Django Framework)

Database : SQLite

Communication : Twilio / Plivo API (for IVR & SMS)
Data Source : Government Open Data API (data.gov.in)

## Project structure
```
Agri-Genix/
├── app.py              # Main Flask application logic
├── models.py           # SQLite Database models
├── requirements.txt    # Python dependencies
├── static/             # CSS, JS, and Images
└── templates/          # HTML Templates (Farmer Dashboard, Buyer View, Login)
```

## ⚙️ Installation & Setup
Clone the repository:
```
Bash
git clone https://github.com/your-username/agri-genix.git
cd agri-genix
```
Create a virtual environment:
```
Bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```
Install dependencies:
```
Bash
pip install flask flask_sqlalchemy requests twilio
```
Run the application:
```
Bash
python app.py
```
## 📈 Future Roadmap
AI Price Prediction: Predict market rates for crops using historical data.

Multilingual Support: Localizing the platform and IVR for regional languages.

Payment Gateway: Integrated escrow system for secure online payments.
