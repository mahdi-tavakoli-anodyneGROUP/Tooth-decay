import uvicorn
from fastapi import FastAPI, Form, UploadFile, File, Request, Depends, BackgroundTasks
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session
import base64
from database import engine, Base, SessionLocal
from database_model import User, PredictionLog, LoginLog
import auth, model
from users import create_user
from recommendations import ICDAS_RECOMMENDATIONS
from pdf_generator import generate_prediction_pdf
import asyncio
import gc
import torch
import io
import numpy as np
from PIL import Image
import concurrent.futures
import time
import json
from pydantic import BaseModel, Field
from typing import Dict, Optional

Base.metadata.create_all(bind=engine)
app = FastAPI()

class PDFReportData(BaseModel):
    model_name: Optional[str] = 'Advanced Dental AI'
    total_detections: Optional[int] = 0
    confidence_score: Optional[float] = 0.0
    execution_time: Optional[float] = 0.0
    class_counts: Optional[Dict[str, int]] = Field(default_factory=dict)
    patient_name: Optional[str] = None

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    html_content = """
    <!DOCTYPE html>
    <html lang="en" data-theme="light">
    <head>
      <title>Prediction Service</title>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
      <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
      <style>
        :root {
            --primary-color: #1a1f2c;
            --secondary-color: #64ffda;
            --accent-color: #88cfff;
            --background-color: #0a0d14;
            --card-bg: rgba(30, 35, 45, 0.95);
            --text-color: #ffffff;
            --text-bright: #e2e8f0;  
            --text-muted: #a6accd;
            --gradient-start: #64ffda;
            --gradient-end: #88cfff;
            --input-bg: rgba(166, 172, 205, 0.08);
            --warning-color: #ffd700;
            --placeholder-color: #8b95b4;  
            --success-color: #28a745;
            --error-color: #ff4444;
        }

        body { 
          background-color: var(--background-color);
            min-height: 100vh;
            color: var(--text-color);
            margin: 0;
            padding: 2rem;
            font-family: 'Poppins', sans-serif;
        }

        
        .container {
            max-width: 1440px;
            margin: 0 auto;
            padding: 2rem 1rem;
        }

        
        .site-header {
            text-align: center;
            padding: 2rem 1rem 4rem;
            margin-bottom: 2rem;
        }

        .site-header h1 {
            font-size: 3.5rem;
            font-weight: 700;
            margin-bottom: 1rem;
            background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-transform: uppercase;
        }

        .site-header p {
            font-size: 1.5rem;
            color: var(--text-muted);
            margin: 0;
        }

        /* Grid Layout */
        .grid-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 2rem;
            padding: 1rem;
            justify-items: center;
            justify-content: center;
        }

        /* Card Styles */
        .card { 
            width: 100%;
            max-width: 380px;
            min-height: 520px; /* Changed from fixed height to min-height */
            background: var(--card-bg);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(100, 255, 218, 0.1);
            border-radius: 20px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }

        /* Prediction Card Specific */
        .card.prediction-card {
            min-height: 580px; /* Changed from fixed height to min-height */
        }

        .card-body {
            padding: 1.5rem;
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow-y: auto;
        }

        /* Center login/signup form when few inputs */
        .card:not(.prediction-card) .card-body {
            justify-content: center;
        }

        /* Consistent form group spacing */
        .card-body .form-group {
            margin-bottom: 1.5rem;
        }

        /* Drag Zone with fixed height */
        .drag-zone {
            height: 220px; /* Fixed height */
            min-height: 220px; /* Prevent shrinking */
            border: 2px dashed var(--secondary-color);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            transition: all 0.3s ease;
            background: var(--input-bg);
        }

        /* Token Input Group */
        .token-input-group {
            position: relative;
            display: flex; /* Use flexbox for alignment */
            align-items: center; /* Align items vertically */
        }

        .token-input-group .form-control {
            height: 50px;
            /* padding-right: 50px; */ /* Space for paste button - adjusted by flex */
            flex-grow: 1; /* Allow input to take available space */
            margin-right: 0.5rem; /* Space between input and button */
        }

        .btn-paste {
            background: rgba(100, 255, 218, 0.1);
            border: 1px solid rgba(100, 255, 218, 0.2);
            color: var(--secondary-color);
            min-width: 42px;
            width: 42px; /* Fixed width */
            height: 42px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.3s ease;
            padding: 0;
            flex-shrink: 0; /* Prevent button from shrinking */
        }

        .btn-paste:hover {
            background: rgba(100, 255, 218, 0.2);
            transform: translateY(-2px);
        }
        
        .btn-paste.pasted {
            background: rgba(100,255,218,0.3) !important;
            transform: translateY(-1px) !important;
            transition: background 0.2s, transform 0.2s;
        }

        .btn-paste i {
            font-size: 1.1rem;
        }

        /* Card Headers */
        .card-header {
            background: linear-gradient(135deg, rgba(100, 255, 218, 0.1), rgba(136, 207, 255, 0.1));
            border-bottom: 2px solid var(--secondary-color);
            color: var(--secondary-color);
            font-size: 1.5rem;
            font-weight: 600;
            padding: 1.5rem;
            border-radius: 20px 20px 0 0;
        }

        .card-header i {
            font-size: 1.8rem;
            color: var(--secondary-color);
            margin-right: 0.75rem;
        }

        .card-header span {
            font-size: 1.5rem;
            font-weight: 600;
            color: var(--secondary-color);
        }

        /* Form Controls */
        .form-control {
            background: var(--input-bg);
            border: 1px solid rgba(100, 255, 218, 0.2);
            border-radius: 12px;
            padding: 12px 16px;
            color: var(--text-bright);  /* Brighter text color */
            width: 100%;
            transition: all 0.3s ease;
            margin-top: 19px;
        }

        .form-control::placeholder {
            color: var(--placeholder-color);  /* Brighter placeholder text */
        }

        /* Labels and headings */
        .form-label {
            color: var(--text-bright);  /* Brighter label color */
            margin-bottom: 8px;
            display: block;
            font-weight: 500;
        }

        /* Upload section */
        .upload-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }

        .upload-header .form-label {
            color: var(--text-bright);  /* Brighter upload label */
        }

        .size-limit {
            color: var(--warning-color);
            font-size: 0.9rem;
            font-weight: 500;
        }

        /* File info */
        .file-details {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }

            color: var(--text-bright);  /* Brighter filename text */
            font-size: 0.9rem;
        }

        .size-info {
            color: var(--secondary-color);
            font-weight: 500;
        }

        /* Drag Zone */
        .drag-zone i {
            font-size: 3rem;
            color: var(--secondary-color);
            margin-bottom: 1rem;
        }

        .drag-zone h5 {
            font-size: 1.2rem;
            margin: 0.5rem 0;
            color: var(--text-color);
        }

        .drag-zone p {
            color: var(--text-muted);
            margin: 0;
        }

        /* Button Styles */
        .btn {
            background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
            border: none;
            border-radius: 12px;
            color: var(--primary-color);
            font-size: 1.1rem;
          font-weight: 600;
            padding: 0.875rem 1.5rem;
            width: 100%;
            margin-top: 19px;
            cursor: pointer;
          transition: all 0.3s ease;
        }

        .btn:hover {
          transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(100, 255, 218, 0.2);
        }

        /* Add this to your existing styles */
        .btn-paste.pasted {
            background: rgba(100,255,218,0.3) !important;
            transform: translateY(-1px) !important;
            transition: background 0.2s, transform 0.2s;
        }
      </style>
    </head>
    <body>
        <!-- Updated HTML Structure -->
        <div class="container">
            <!-- Header -->
            <header class="site-header">
                <h1>ANODYNE TEAM</h1>
                <p>Intelligent Dental Imaging & Analysis System</p>
            </header>

            <!-- Cards Grid -->
            <div class="grid-container">
        <!-- Login Card -->
        <div class="card">
                    <div class="card-header">
                        <i class="fas fa-sign-in-alt"></i>
                        Login
                    </div>
          <div class="card-body">
            <form action="/login" method="post">
                            <div class="form-group">
                                <input type="text" name="username" class="form-control" placeholder="Username" required>
                            </div>
                            <div class="form-group">
                                <input type="password" name="password" class="form-control" placeholder="Password" required>
                            </div>
                            <button type="submit" class="btn login-btn">Login</button>
            </form>
          </div>
        </div>

        <!-- Sign Up Card -->
        <div class="card">
                    <div class="card-header">
                        <i class="fas fa-user-plus"></i>
                        Sign Up
                    </div>
          <div class="card-body">
            <form action="/signup" method="post">
                            <div class="form-group">
                                <input type="text" name="username" class="form-control" placeholder="Username" required>
                            </div>
                            <div class="form-group">
                                <input type="email" name="email" class="form-control" placeholder="Email" required>
                            </div>
                            <div class="form-group">
                                <input type="password" name="password" class="form-control" placeholder="Password" required>
                            </div>
                            <button type="submit" class="btn signup-btn">Sign Up</button>
            </form>
          </div>
        </div>

        <!-- Prediction Card -->
                <div class="card prediction-card">
                    <div class="card-header">
                        <i class="fas fa-brain"></i>
                        Predict Image
                    </div>
          <div class="card-body">
            <form action="/predict" method="post" enctype="multipart/form-data" id="predictForm">
                            <div class="form-group">
                                <div class="upload-header">
                                    <label class="form-label">Upload Image</label>
                                    <span class="size-limit">Max size: 2 MB</span>
                                </div>
                                <div class="file-upload">
                                    <input type="file" name="file" id="fileInput" class="form-control" accept="image/*" required>
                                    <div class="file-info" id="fileInfo">
                                        <div class="file-details">
                                            <span id="fileName">No file chosen</span>
                                            <span id="fileSize" class="size-info"></span>
                                        </div>
                                        <div class="progress">
                                            <div class="progress-bar" id="sizeProgress" role="progressbar"></div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="form-group">
                                <label class="form-label">Enter Token</label>
                                <div class="token-input-group">
                                    <input type="text" name="token" id="predictToken" class="form-control" placeholder="Enter token here" required>
                                    <button type="button" class="btn-paste" id="pasteTokenButton" title="Paste Token">
                                        <i class="fas fa-paste"></i>
                                    </button>
                                </div>
                            </div>

                            <button type="submit" class="btn predict-btn">
                                <i class="fas fa-wand-magic-sparkles"></i> Predict
                            </button>
            </form>
          </div>
        </div>
      </div>
        </div>

        <!-- Scripts -->
      <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        <script>
            document.addEventListener('DOMContentLoaded', () => {
                const fileInput = document.getElementById('fileInput');
                const predictForm = document.getElementById('predictForm');
                const fileNameDisplay = document.getElementById('fileName');
                const fileSizeDisplay = document.getElementById('fileSize');
                const sizeProgressBar = document.getElementById('sizeProgress');
                const maxSize = 2 * 1024 * 1024; // 2 MB
                const predictTokenInput = document.getElementById('predictToken');
                const pasteTokenButton = document.getElementById('pasteTokenButton');
                
                if (fileInput) {
                    fileInput.addEventListener('change', () => {
                        const file = fileInput.files[0];
                        if (file) {
                            fileNameDisplay.textContent = file.name;
                            const fileSizeMB = (file.size / 1024 / 1024).toFixed(2);
                            fileSizeDisplay.textContent = fileSizeMB + ' MB';

                            const pct = Math.min((file.size / maxSize) * 100, 100);
                            sizeProgressBar.style.width = pct + '%';
                            sizeProgressBar.style.backgroundColor = ''; // Reset color
                            sizeProgressBar.classList.remove('bg-danger', 'bg-success');

                            if (file.size > maxSize) {
                                sizeProgressBar.classList.add('bg-danger');
                            } else {
                                sizeProgressBar.classList.add('bg-success');
                            }
                            document.getElementById('fileInfo').style.display = 'block';
                        } else {
                            fileNameDisplay.textContent = 'No file chosen';
                            fileSizeDisplay.textContent = '';
                            sizeProgressBar.style.width = '0%';
                            sizeProgressBar.classList.remove('bg-danger', 'bg-success');
                            document.getElementById('fileInfo').style.display = 'none';
                        }
                    });
                }

                if (pasteTokenButton && predictTokenInput) {
                    pasteTokenButton.addEventListener('click', async () => {
                        try {
                            const text = await navigator.clipboard.readText();
                            predictTokenInput.value = text;
                            pasteTokenButton.classList.add('pasted');
                            setTimeout(() => {
                                pasteTokenButton.classList.remove('pasted');
                            }, 1000); // Visual feedback for 1 second
                        } catch (err) {
                            console.error('Failed to read clipboard contents: ', err);
                            // Optionally, inform the user that paste failed
                            alert('Failed to paste token. Please try manually or check browser permissions.');
                        }
                    });
                }

                const savedToken = localStorage.getItem('apiUserToken');
                if (savedToken && predictTokenInput) {
                    predictTokenInput.value = savedToken;
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/signup", response_class=HTMLResponse)
async def signup(username: str = Form(...), email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    try:
        user_instance = create_user(db, username=username, email=email, password=password)
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en" data-theme="light">
        <head>
          <title>Sign Up Successful</title>
          <meta charset="UTF-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
          <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
          <style>
            :root {{
                --primary-color: #1a1f2c;
                --secondary-color: #64ffda;
                --accent-color: #88cfff;
                --background-color: #0a0d14;
                --card-bg: rgba(30, 35, 45, 0.95);
                --text-color: #ffffff;
                --text-bright: #e2e8f0;
                --text-muted: #a6accd;
                --gradient-start: #64ffda;
                --gradient-end: #88cfff;
                --input-bg: rgba(166, 172, 205, 0.08);
                --warning-color: #ffd700;
                --placeholder-color: #8b95b4;
                --success-color: #28a745;
                --error-color: #ff4444;
            }}

            body {{ 
                background-color: var(--background-color);
                min-height: 100vh;
                color: var(--text-color);
                margin: 0;
                padding: 2rem;
                font-family: 'Poppins', sans-serif;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: flex-start; /* Align to top */
            }}

            .container-custom {{ /* Renamed from .container to avoid conflict with bootstrap */
                max-width: 800px;
                width: 100%;
                margin-top: 2rem; /* Add some margin at the top */
            }}

            .card {{ 
                width: 100%;
                background: var(--card-bg);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(100, 255, 218, 0.1);
                border-radius: 20px;
                overflow: hidden;
                display: flex;
                flex-direction: column;
                box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
            }}

            .card-header {{
                background: linear-gradient(135deg, rgba(100, 255, 218, 0.1), rgba(136, 207, 255, 0.1));
                border-bottom: 2px solid var(--success-color);
                color: var(--success-color);
                font-size: 1.5rem;
                font-weight: 600;
                padding: 1.5rem;
                border-radius: 20px 20px 0 0;
                text-align: center;
            }}
            
            .card-header.error {{
                border-bottom: 2px solid var(--error-color);
                color: var(--error-color);
            }}

            .card-header i {{
                font-size: 1.8rem;
                margin-right: 0.75rem;
            }}

            .card-body {{
                padding: 2rem;
                flex: 1;
                text-align: center;
            }}

            .btn {{
                background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
                border: none;
                border-radius: 12px;
                color: var(--primary-color);
                font-size: 1.1rem;
                font-weight: 600;
                padding: 0.875rem 1.5rem;
                cursor: pointer;
                transition: all 0.3s ease;
                margin-top: 1.5rem; /* Adjusted margin */
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
            }}

            .btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(100, 255, 218, 0.2);
            }}
            
            .site-header {{
                text-align: center;
                padding-bottom: 2rem; /* Reduced padding */
                width: 100%;
                max-width: 1440px; /* Consistent with main page header */
            }}

            .site-header h1 {{
                font-size: 3.5rem; /* Consistent with main page header */
                font-weight: 700;
                margin-bottom: 1rem;
                background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                text-transform: uppercase;
            }}

            .site-header p {{
                font-size: 1.5rem; /* Consistent with main page header */
                color: var(--text-muted);
                margin: 0;
            }}
            
            .alert-message {{ /* Style for the success message text */
                color: var(--text-bright); 
                font-size: 1.1rem; 
                margin-bottom: 1.5rem;
            }}
            .icon-large {{
                font-size: 3rem;
                margin-bottom: 1rem;
            }}
            .icon-success {{ color: var(--success-color); }}
          </style>
        </head>
        <body>
          <header class="site-header">
              <h1>ANODYNE TEAM</h1>
              <p>Intelligent Dental Imaging & Analysis System</p>
          </header>
          
          <div class="container-custom">
            <div class="card">
              <div class="card-header">
                <i class="fas fa-check-circle"></i>
                Sign Up Successful
              </div>
              <div class="card-body">
                <i class="fas fa-user-check icon-large icon-success"></i>
                <p class="alert-message">Welcome, <strong>{user_instance.username}</strong>! Your account has been created. You can now log in.</p>
                <a href="/" class="btn">
                    <i class="fas fa-home"></i>
                    Return Home
                </a>
              </div>
            </div>
          </div>
          <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
    except ValueError as e:
        error_message = str(e)
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en" data-theme="light">
        <head>
          <title>Sign Up Failed</title>
          <meta charset="UTF-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
          <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
          <style>
            :root {{
                --primary-color: #1a1f2c;
                --secondary-color: #64ffda;
                --accent-color: #88cfff;
                --background-color: #0a0d14;
                --card-bg: rgba(30, 35, 45, 0.95);
                --text-color: #ffffff;
                --text-bright: #e2e8f0;
                --text-muted: #a6accd;
                --gradient-start: #64ffda;
                --gradient-end: #88cfff;
                --input-bg: rgba(166, 172, 205, 0.08);
                --warning-color: #ffd700;
                --placeholder-color: #8b95b4;
                --success-color: #28a745;
                --error-color: #ff4444;
            }}

            body {{ 
                background-color: var(--background-color);
                min-height: 100vh;
                color: var(--text-color);
                margin: 0;
                padding: 2rem;
                font-family: 'Poppins', sans-serif;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: flex-start; /* Align to top */
            }}

            .container-custom {{ /* Renamed from .container to avoid conflict with bootstrap */
                max-width: 800px;
                width: 100%;
                margin-top: 2rem; /* Add some margin at the top */
            }}

            .card {{ 
                width: 100%;
                background: var(--card-bg);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(100, 255, 218, 0.1);
                border-radius: 20px;
                overflow: hidden;
                display: flex;
                flex-direction: column;
                box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
            }}

            .card-header {{
                background: linear-gradient(135deg, rgba(100, 255, 218, 0.1), rgba(136, 207, 255, 0.1));
                border-bottom: 2px solid var(--error-color);
                color: var(--error-color);
                font-size: 1.5rem;
                font-weight: 600;
                padding: 1.5rem;
                border-radius: 20px 20px 0 0;
                text-align: center;
            }}

            .card-header i {{
                font-size: 1.8rem;
                margin-right: 0.75rem;
            }}

            .card-body {{
                padding: 2rem;
                flex: 1;
                text-align: center;
            }}

            .btn {{
                background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
                border: none;
                border-radius: 12px;
                color: var(--primary-color);
                font-size: 1.1rem;
                font-weight: 600;
                padding: 0.875rem 1.5rem;
                cursor: pointer;
                transition: all 0.3s ease;
                margin-top: 1.5rem; /* Adjusted margin */
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
            }}

            .btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(100, 255, 218, 0.2);
            }}
            
            .site-header {{
                text-align: center;
                padding-bottom: 2rem; /* Reduced padding */
                width: 100%;
                max-width: 1440px; /* Consistent with main page header */
            }}

            .site-header h1 {{
                font-size: 3.5rem; /* Consistent with main page header */
                font-weight: 700;
                margin-bottom: 1rem;
                background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                text-transform: uppercase;
            }}

            .site-header p {{
                font-size: 1.5rem; /* Consistent with main page header */
                color: var(--text-muted);
                margin: 0;
            }}

            .alert-message {{ /* Style for the error message text */
                color: var(--text-bright); 
                font-size: 1.1rem; 
                margin-bottom: 1.5rem;
            }}
            .icon-large {{
                font-size: 3rem;
                margin-bottom: 1rem;
            }}
            .icon-error {{ color: var(--error-color); }}
          </style>
        </head>
        <body>
          <header class="site-header">
              <h1>ANODYNE TEAM</h1>
              <p>Intelligent Dental Imaging & Analysis System</p>
          </header>
          
          <div class="container-custom">
            <div class="card">
              <div class="card-header error">
                  <i class="fas fa-exclamation-circle"></i>
                  Sign Up Failed
              </div>
              <div class="card-body text-center">
                  <i class="fas fa-times-circle icon-large icon-error"></i>
                  <p class="alert-message">{error_message}</p>
                  <a href="/" class="btn">
                      <i class="fas fa-undo"></i>
                      Try Again
                  </a>
              </div>
            </div>
          </div>
          <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content, status_code=400)
    except Exception as e: # General server error
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en" data-theme="light">
        <head>
          <title>Sign Up Failed - Server Error</title>
          <meta charset="UTF-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
          <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
          <style>
            :root {{
                --primary-color: #1a1f2c;
                --secondary-color: #64ffda;
                --accent-color: #88cfff;
                --background-color: #0a0d14;
                --card-bg: rgba(30, 35, 45, 0.95);
                --text-color: #ffffff;
                --text-bright: #e2e8f0;
                --text-muted: #a6accd;
                --gradient-start: #64ffda;
                --gradient-end: #88cfff;
                --input-bg: rgba(166, 172, 205, 0.08);
                --warning-color: #ffd700;
                --placeholder-color: #8b95b4;
                --success-color: #28a745;
                --error-color: #ff4444;
            }}

            body {{ 
                background-color: var(--background-color);
                min-height: 100vh;
                color: var(--text-color);
                margin: 0;
                padding: 2rem;
                font-family: 'Poppins', sans-serif;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: flex-start; /* Align to top */
            }}

            .container-custom {{ /* Renamed from .container to avoid conflict with bootstrap */
                max-width: 800px;
                width: 100%;
                margin-top: 2rem; /* Add some margin at the top */
            }}

            .card {{ 
                width: 100%;
                background: var(--card-bg);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(100, 255, 218, 0.1);
                border-radius: 20px;
                overflow: hidden;
                display: flex;
                flex-direction: column;
                box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
            }}

            .card-header {{
                background: linear-gradient(135deg, rgba(100, 255, 218, 0.1), rgba(136, 207, 255, 0.1));
                border-bottom: 2px solid var(--error-color);
                color: var(--error-color);
                font-size: 1.5rem;
                font-weight: 600;
                padding: 1.5rem;
                border-radius: 20px 20px 0 0;
                text-align: center;
            }}

            .card-header i {{
                font-size: 1.8rem;
                margin-right: 0.75rem;
            }}

            .card-body {{
                padding: 2rem;
                flex: 1;
                text-align: center;
            }}

            .btn {{
                background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
                border: none;
                border-radius: 12px;
                color: var(--primary-color);
                font-size: 1.1rem;
                font-weight: 600;
                padding: 0.875rem 1.5rem;
                cursor: pointer;
                transition: all 0.3s ease;
                margin-top: 1.5rem; /* Adjusted margin */
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
            }}

            .btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(100, 255, 218, 0.2);
            }}
            
            .site-header {{
                text-align: center;
                padding-bottom: 2rem; /* Reduced padding */
                width: 100%;
                max-width: 1440px; /* Consistent with main page header */
            }}

            .site-header h1 {{
                font-size: 3.5rem; /* Consistent with main page header */
                font-weight: 700;
                margin-bottom: 1rem;
                background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                text-transform: uppercase;
            }}

            .site-header p {{
                font-size: 1.5rem; /* Consistent with main page header */
                color: var(--text-muted);
                margin: 0;
            }}

            .alert-message {{ /* Style for the error message text */
                color: var(--text-bright); 
                font-size: 1.1rem; 
                margin-bottom: 1.5rem;
            }}
            .icon-large {{
                font-size: 3rem;
                margin-bottom: 1rem;
            }}
            .icon-error {{ color: var(--error-color); }}
          </style>
        </head>
        <body>
          <header class="site-header">
              <h1>ANODYNE TEAM</h1>
              <p>Intelligent Dental Imaging & Analysis System</p>
          </header>
          
          <div class="container-custom">
            <div class="card">
              <div class="card-header error">
                  <i class="fas fa-server"></i>
                  Server Error
              </div>
              <div class="card-body text-center">
                  <i class="fas fa-cogs icon-large icon-error"></i>
                  <p class="alert-message">An unexpected error occurred on the server. Please try again later.</p>
                  <a href="/" class="btn">
                      <i class="fas fa-home"></i>
                      Return Home
                  </a>
              </div>
            </div>
          </div>
          <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content, status_code=500)

@app.post("/login", response_class=HTMLResponse)
async def login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    if not auth.authenticate_user(db, username, password):
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en" data-theme="light">
        <head>
          <title>Login Failed</title>
          <meta charset="UTF-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
          <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
          <style>
            :root {{
                --primary-color: #1a1f2c;
                --secondary-color: #64ffda;
                --accent-color: #88cfff;
                --background-color: #0a0d14;
                --card-bg: rgba(30, 35, 45, 0.95);
                --text-color: #ffffff;
                --text-bright: #e2e8f0;
                --text-muted: #a6accd;
                --gradient-start: #64ffda;
                --gradient-end: #88cfff;
                --input-bg: rgba(166, 172, 205, 0.08);
                --error-color: #ff4444;
            }}

            body {{ 
                background-color: var(--background-color);
                min-height: 100vh;
                color: var(--text-color);
                margin: 0;
                padding: 2rem;
                font-family: 'Poppins', sans-serif;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: flex-start; /* Align to top */
            }}

            .container-custom {{ 
                max-width: 800px;
                width: 100%;
                margin-top: 2rem;
            }}

            .card {{ 
                width: 100%;
                background: var(--card-bg);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(100, 255, 218, 0.1);
                border-radius: 20px;
                overflow: hidden;
                display: flex;
                flex-direction: column;
                box-shadow: 0 10px 20px rgba(0,0,0,0.2);
            }}

            .card-header {{
                background: linear-gradient(135deg, rgba(100,255,218,0.1), rgba(136,207,255,0.1));
                border-bottom: 2px solid var(--error-color);
                color: var(--error-color);
                font-size: 1.5rem;
                font-weight: 600;
                padding: 1.5rem;
                border-radius: 20px 20px 0 0;
                text-align: center;
            }}

            .card-header i {{
                font-size: 1.8rem;
                margin-right: 0.75rem;
            }}
            
            .card-body {{
                padding: 2rem;
                flex: 1;
                text-align: center;
            }}

            .btn {{
                background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
                border: none;
                border-radius: 12px;
                color: var(--primary-color);
                font-size: 1.1rem;
                font-weight: 600;
                padding: 0.875rem 1.5rem;
                cursor: pointer;
                transition: all 0.3s ease;
                margin-top: 1.5rem;
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
            }}

            .btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(100, 255, 218, 0.2);
            }}
            
            .site-header {{
                text-align: center;
                padding-bottom: 2rem;
                width: 100%;
                max-width: 1440px;
            }}

            .site-header h1 {{
                font-size: 3.5rem;
                font-weight: 700;
                margin-bottom: 1rem;
                background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                text-transform: uppercase;
            }}

            .site-header p {{
                font-size: 1.5rem;
                color: var(--text-muted);
                margin: 0;
            }}
            
            .alert-message {{ 
                color: var(--text-bright); 
                font-size: 1.1rem; 
                margin-bottom: 1.5rem;
            }}
            .icon-large {{
                font-size: 3rem;
                margin-bottom: 1rem;
            }}
            .icon-error {{ color: var(--error-color); }}
          </style>
        </head>
        <body>
            <header class="site-header">
                <h1>ANODYNE TEAM</h1>
                <p>Intelligent Dental Imaging & Analysis System</p>
            </header>
            <div class="container-custom">
                <div class="card">
                    <div class="card-header">
                        <i class="fas fa-exclamation-triangle"></i>Login Failed
                    </div>
                    <div class="card-body">
                        <i class="fas fa-times-circle icon-large icon-error"></i>
                        <p class="alert-message">Invalid username or password. Please check your credentials and try again.</p>
                        <a href="/" class="btn">
                            <i class="fas fa-home"></i>Return Home
                        </a>
                    </div>
                </div>
            </div>
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content, status_code=401)

    token = auth.create_access_token({"sub": username})
    user_obj = db.query(User).filter(User.username == username).first()
    new_log = LoginLog(user_id=user_obj.id)
    db.add(new_log)
    db.commit()
    db.refresh(new_log)

    admin_list_html = ""
    if user_obj.is_admin:
        from datetime import date, datetime
        today = date.today()
        start_of_day = datetime(today.year, today.month, today.day, 0, 0, 0)
        logs_today = db.query(LoginLog).join(User, LoginLog.user_id == User.id).filter(LoginLog.login_time >= start_of_day).all()
        user_list_items = "".join([
            f"""<li class='list-group-item d-flex justify-content-between align-items-center' style='background-color: var(--input-bg); color: var(--text-bright); border-color: rgba(100,255,218,0.2);'>
                {log.user.username}
                <span class='badge' style='background-color: var(--secondary-color); color: var(--primary-color);'>{log.login_time.strftime('%H:%M')}</span>
            </li>""" for log in logs_today
        ])
        admin_list_html = f"""
        <div class="card mt-4" style="background: var(--card-bg); border: 1px solid rgba(100,255,218,0.1);">
            <div class="card-header admin-header" style="background: linear-gradient(135deg, rgba(100,255,218,0.1), rgba(136,207,255,0.1)); border-bottom: 2px solid var(--accent-color); color: var(--accent-color);">
                <i class="fas fa-users-cog me-2"></i>Users Logged In Today
            </div>
          <ul class="list-group list-group-flush">
            {user_list_items}
          </ul>
        </div>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en" data-theme="light">
    <head>
      <title>Login Successful</title>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
      <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
      <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600&family=Roboto+Mono&display=swap" rel="stylesheet">
      <style>
        :root {{
            --primary-color: #1a1f2c;
            --secondary-color: #64ffda;
            --accent-color: #88cfff;
            --background-color: #0a0d14;
            --card-bg: rgba(30, 35, 45, 0.95);
            --text-color: #ffffff;
            --text-bright: #e2e8f0;
            --text-muted: #a6accd;
            --gradient-start: #64ffda;
            --gradient-end: #88cfff;
            --input-bg: rgba(166, 172, 205, 0.08);
            --success-color: #28a745;
        }}
        
        body {{ 
            background-color: var(--background-color);
            min-height: 100vh;
            color: var(--text-color);
            margin: 0;
            padding: 2rem;
            font-family: 'Poppins', sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: flex-start;
        }}
        
        .container-custom {{ 
            max-width: 800px;
            width: 100%;
            margin-top: 2rem;
        }}

        .card {{ 
            width: 100%;
            background: var(--card-bg);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(100, 255, 218, 0.1);
            border-radius: 20px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        }}

        .card-header {{
            background: linear-gradient(135deg, rgba(100,255,218,0.1), rgba(136,207,255,0.1));
            border-bottom: 2px solid var(--success-color);
            color: var(--success-color);
            font-size: 1.5rem;
            font-weight: 600;
            padding: 1.5rem;
            border-radius: 20px 20px 0 0;
            text-align: center;
        }}

        .card-header i {{
            font-size: 1.8rem;
            margin-right: 0.75rem;
        }}
        
        .card-body {{
            padding: 2rem;
            flex: 1;
            text-align: center;
        }}

        .token-info-container {{
            background: var(--input-bg);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            border: 1px solid rgba(100,255,218,0.2);
        }}
        
            word-break: break-all;
            margin-bottom: 1rem;
            font-family: 'Roboto Mono', monospace;
            font-size: 1rem;
            padding: 1rem;
            background: rgba(0,0,0,0.3);
            border-radius: 8px;
            color: var(--text-bright);
            border: 1px solid rgba(100,255,218,0.1);
            text-align: left;
        }}
        
        .copy-feedback {{
            background: var(--success-color);
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            font-size: 0.9rem;
            margin-bottom: 1rem;
            display: none; /* Initially hidden */
        }}

        .btn {{
            background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
            border: none;
            border-radius: 12px;
            color: var(--primary-color) !important; /* Ensure text color is primary */
            font-size: 1.1rem;
            font-weight: 600;
            padding: 0.875rem 1.5rem;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }}

        .btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(100, 255, 218, 0.2);
        }}
        
        .btn.copy-btn {{
             background: rgba(100,255,218,0.1);
             border: 1px solid var(--secondary-color);
             color: var(--secondary-color) !important;
        }}

        .btn.copy-btn:hover {{
            background: rgba(100,255,218,0.2);
            color: var(--accent-color) !important;
        }}

        .site-header {{
            text-align: center;
            padding-bottom: 2rem;
            width: 100%;
            max-width: 1440px;
        }}

        .site-header h1 {{
            font-size: 3.5rem;
            font-weight: 700;
            margin-bottom: 1rem;
            background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-transform: uppercase;
        }}

        .site-header p {{
            font-size: 1.5rem;
            color: var(--text-muted);
            margin: 0;
        }}

        .token-title {{
            color: var(--text-bright);
            font-size: 1.5rem;
            font-weight: 500;
            margin-bottom: 0.5rem;
        }}
        .token-subtitle {{
            color: var(--text-muted);
            font-size: 1rem;
            margin-bottom: 1.5rem;
        }}
        .icon-large {{
            font-size: 3rem;
            margin-bottom: 1rem;
        }}
        .icon-success {{ color: var(--success-color); }}
      </style>
    </head>
    <body>
        <header class="site-header">
            <h1>ANODYNE TEAM</h1>
            <p>Intelligent Dental Imaging & Analysis System</p>
        </header>

        <div class="container-custom">
            <div class="card">
                <div class="card-header">
                    <i class="fas fa-key"></i>Login Successful
                </div>
                <div class="card-body">
                    <i class="fas fa-shield-alt icon-large icon-success"></i>
                    <h4 class="token-title">Your Access Token</h4>
                    <p class="token-subtitle">Keep this token secure. You'll need it for API requests.</p>
                    
                    <div class="token-info-container">
                        <div class="copy-feedback" id="copyFeedback">
                            <i class="fas fa-check me-2"></i>Token copied!
                        </div>
                        <div id="tokenText">{token}</div>
                        <button id="copyButton" class="btn copy-btn mt-3">
                            <i class="fas fa-copy me-2"></i>Copy Token
                        </button>
                    </div>
                    
                    <a href="/" class="btn">
                        <i class="fas fa-home me-2"></i>Return Home
                    </a>
                </div>
            </div>
            {admin_list_html}
        </div>

      <script>
        document.getElementById('copyButton').addEventListener('click', async function() {{
          const tokenText = document.getElementById('tokenText').innerText;
          const feedback = document.getElementById('copyFeedback');
          
          try {{
              await navigator.clipboard.writeText(tokenText);
              showCopyFeedback();
          }} catch (err) {{
              const textArea = document.createElement('textarea');
              textArea.value = tokenText;
              textArea.style.position = 'fixed'; 
              textArea.style.left = '-9999px'; /* Move off-screen */
              textArea.style.opacity = '0';
              document.body.appendChild(textArea);
              textArea.select();
              try {{
                  document.execCommand('copy');
                  showCopyFeedback();
              }} catch (err) {{
                  console.error('Fallback copy failed:', err);
                  alert('Failed to copy token. Please copy it manually.');
              }}
              document.body.removeChild(textArea);
          }}
        }});

        function showCopyFeedback() {{
          const feedback = document.getElementById('copyFeedback');
          feedback.style.display = 'inline-block'; /* Show feedback */
          setTimeout(() => {{
            feedback.style.display = 'none'; /* Hide after 2 seconds */
          }}, 2000);
        }}
      </script>
      <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/request_pdf_download", response_class=Response)
async def request_pdf_download(report_data_json: str = Form(...)):
    try:
        report_data_dict = json.loads(report_data_json)
        pdf_params = PDFReportData(**report_data_dict)

        prediction_data_for_pdf = {
            'model_name': pdf_params.model_name,
            'total_detections': pdf_params.total_detections,
            'confidence_score': pdf_params.confidence_score,
            'execution_time': pdf_params.execution_time,
            'class_counts': pdf_params.class_counts
        }

        pdf_bytes = generate_prediction_pdf(
            prediction_data_for_pdf, 
            ICDAS_RECOMMENDATIONS, 
            patient_name=pdf_params.patient_name
        )
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=dental_analysis_report.pdf"}
        )
    except json.JSONDecodeError:
        return HTMLResponse(content="Error: Invalid report data format.", status_code=400)
    except Exception as e:
        print(f"Error generating PDF for download: {e}")
        return HTMLResponse(content=f"Error generating PDF: {str(e)}", status_code=500)

async def cleanup_resources():
    """Clean up resources after prediction"""
    await asyncio.sleep(1)  # Wait for response to be sent
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

@app.post("/predict", response_class=HTMLResponse)
async def predict(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...), 
    token: str = Form(...), 
    db: Session = Depends(get_db)
):
    username = auth.verify_token(token)
    if not username:
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <title>Token Error</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="container mt-4">
            <div class="card text-center border-danger">
                <div class="card-header bg-danger text-white">Token Error</div>
                <div class="card-body">
                    <p class="card-text">Invalid or expired token.</p>
                    <a href="/" class="btn btn-primary">Return Home</a>
                </div>
            </div>
        </body>
        </html>
        """, status_code=401)
    
    try:
        contents = await file.read()
        
        result = model.predict_image(contents)
        processed_image_bytes = result["processed_image"] # Assuming this is already bytes
        
        pdf_report_data_for_js = {
            'model_name': result.get('model_name', 'Advanced Dental AI'),
            'total_detections': result.get('total_detections', 0),
            'confidence_score': result.get('confidence_score', 0.0),
            'execution_time': result.get('execution_time', 0.0),
            'class_counts': result.get('class_counts', {}),
            'patient_name': None # Or extract if available, e.g. from token or form
        }
        pdf_report_data_json_for_script = json.dumps(pdf_report_data_for_js)

        base64_image = base64.b64encode(processed_image_bytes).decode('utf-8')
        
        await file.close()
        background_tasks.add_task(cleanup_resources)
        
        class_counts_html = "".join([
            f"""
            <div class="detection-item">
                <span class="detection-label">{cls}</span>
                <span class="detection-count">{count}</span>
            </div>
            """
            for cls, count in result["class_counts"].items()
        ])
        
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <title>Prediction Result</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
            <style>
                :root {{
                    --base-color: #1a1f2c;
                    --secondary-color: #64ffda;
                    --accent-color: #88cfff;
                    --background-color: #0a0d14;
                    --card-bg: rgba(30, 35, 45, 0.95);
                    --text-color: #ffffff;
                    --text-bright: #e2e8f0;
                    --text-muted: #a6accd;
                }}

                body {{
                    background-color: var(--background-color);
                    min-height: 100vh;
                    color: var(--text-color);
                    padding: 2rem 0.75rem; /* Reduced side padding for mobile */
                    font-family: 'Poppins', sans-serif;
                    margin: 0;
                }}

                .container {{
                    max-width: 800px;
                    margin: 0 auto;
                    width: 100%;
                }}

                .card {{
                    background: var(--card-bg);
                    backdrop-filter: blur(10px);
                    border: 1px solid rgba(100, 255, 218, 0.1);
                    border-radius: 20px;
                    overflow: hidden;
                }}

                .card-header {{
                    background: rgba(100, 255, 218, 0.1);
                    border-bottom: 1px solid rgba(100, 255, 218, 0.2);
                    padding: 1.5rem;
                    color: var(--secondary-color);
                    font-size: 1.5rem;
                    font-weight: 600;
                }}

                .card-body {{
                    padding: 2rem 1rem; /* Reduced side padding for small screens */
                }}

                .result-container {{
                    background: rgba(255, 255, 255, 0.05);
                    border-radius: 12px;
                    padding: 1.5rem 1rem; /* Reduced side padding for small screens */
                    margin: 1.5rem 0;
                }}

                .result-image {{
                    max-width: 100%;
                    border-radius: 8px;
                    margin: 1rem 0;
                }}

                .icon-main {{
                    color: var(--secondary-color);
                    font-size: 3rem;
                    margin-bottom: 1rem;
                }}

                .analysis-title {{
                    color: var(--accent-color);
                    font-size: 1.8rem;
                    font-weight: 600;
                    margin-bottom: 1.5rem;
                }}

                .section-heading {{
                    color: var(--text-bright);
                    font-size: 1.4rem;
                    font-weight: 500;
                    margin-bottom: 1rem;
                }}

                .stats-container {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); /* Smaller min size */
                    gap: 0.75rem; /* Smaller gap for mobile */
                    margin-top: 1rem;
                }}

                .stat-card {{
                    background: rgba(255, 255, 255, 0.05);
                    padding: 0.75rem; /* Smaller padding */
                    border-radius: 8px;
                    text-align: center;
                }}

                .stat-value {{
                    font-size: 1.25rem; /* Smaller font for mobile */
                    font-weight: 600;
                    color: var(--secondary-color);
                }}

                .stat-label {{
                    color: var(--text-muted);
                    font-size: 0.8rem; /* Smaller font for mobile */
                }}

                .detection-heading {{
                    color: var(--accent-color);
                    font-size: 1.2rem;
                    font-weight: 500;
                    margin-bottom: 1rem;
                }}

                .detection-item {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 0.75rem 1rem;
                    background: rgba(255, 255, 255, 0.05);
                    margin: 0.5rem 0;
                    border-radius: 8px;
                }}

                .detection-label {{
                    color: var(--text-bright);
                    font-weight: 500;
                }}

                .detection-count {{
                    background: var(--secondary-color);
                    color: var(--base-color);
                    padding: 0.25rem 0.75rem;
                    border-radius: 12px;
                    font-weight: 600;
                }}

                /* Button Styles */
                .action-buttons {{
                    display: flex;
                    flex-direction: column; /* Stack buttons vertically by default for mobile */
                    gap: 1rem;
                    justify-content: center;
                    margin-top: 2rem;
                    width: 100%;
                }}

                .btn {{
                    background: linear-gradient(135deg, var(--secondary-color), var(--accent-color));
                    color: var(--base-color);
                    border: none;
                    padding: 1rem; /* More touch-friendly for mobile */
                    border-radius: 12px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    text-decoration: none;
                    display: flex;
                    align-items: center;
                    justify-content: center; /* Center text and icon */
                    gap: 0.5rem;
                    width: 100%; /* Full width on mobile */
                    font-size: 1rem; /* Adjusted font size */
                }}

                .btn i {{
                    font-size: 1.2rem; /* Slightly larger icons */
                }}

                .btn:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(100, 255, 218, 0.2);
                }}

                .btn:active {{
                    transform: translateY(1px); /* Feedback for touch */
                }}

                /* Different color for each button to distinguish them */
                .btn-image {{
                    background: linear-gradient(135deg, #64ffda, #44c4b7);
                }}

                .btn-pdf {{
                    background: linear-gradient(135deg, #ff6464, #ff4444);
                }}

                .btn-home {{
                    background: linear-gradient(135deg, #88cfff, #6499ff);
                }}

                .text-center {{ text-align: center; }}
                .mb-3 {{ margin-bottom: 1rem; }}
                .mb-4 {{ margin-bottom: 1.5rem; }}
                .mt-4 {{ margin-top: 1.5rem; }}
                .me-2 {{ margin-right: 0.5rem; }}

                /* Media queries for larger screens */
                @media (min-width: 768px) {{
                    .card-body {{
                        padding: 2rem;
                    }}

                    .result-container {{
                        padding: 1.5rem;
                    }}

                    .action-buttons {{
                        flex-direction: row; /* Side-by-side on larger screens */
                    }}

                    .btn {{
                        width: auto; /* Auto width on desktop */
                        padding: 0.8rem 1.5rem; /* Original padding */
                    }}

                    .stats-container {{
                        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); /* Original size */
                        gap: 1rem; /* Original gap */
                    }}

                    .stat-value {{
                        font-size: 1.5rem; /* Original font size */
                    }}

                    .stat-label {{
                        font-size: 0.9rem; /* Original font size */
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="card">
                    <div class="card-header">
                        <i class="fas fa-check-circle me-2"></i>
                        Prediction Complete
                    </div>
                    <div class="card-body">
                        <div class="text-center mb-4">
                            <i class="fas fa-microscope icon-main"></i>
                            <h4 class="analysis-title">Analysis Results</h4>
                        </div>
                        
                        <div class="result-container">
                            <h5 class="section-heading">Processed Image</h5>
                            <img src="data:image/png;base64,{base64_image}" 
                                 alt="Processed Image" 
                                 class="result-image mb-3">
                            
                            <div class="stats-container">
                                <div class="stat-card">
                                    <div class="stat-value">{result["total_detections"]}</div>
                                    <div class="stat-label">Total Detections</div>
                                </div>
                                
                                <div class="stat-card">
                                    <div class="stat-value">{result["execution_time"]:.2f}s</div>
                                    <div class="stat-label">Processing Time</div>
                                </div>
                                <div class="stat-card">
                                    <div class="stat-value">{result["confidence_score"]:.2f}</div>
                                    <div class="stat-label">Confidence Score</div>
                                </div>
                            </div>
                            
                            <div class="prediction-info mt-4">
                                <h6 class="detection-heading">Detection Breakdown:</h6>
                                {class_counts_html}
                            </div>
                        </div>
                        
                        <div class="action-buttons">
                            <button class="btn btn-image" id="downloadImageBtn" style="width: 100%;">
                                <i class="fas fa-download"></i>
                                Download Result Image
                            </button>
                            
                            <form id="pdfDownloadForm" action="/request_pdf_download" method="POST" target="_blank" style="margin:0; padding:0; display:inline-block; width: 100%;">
                                <input type="hidden" name="report_data_json" id="pdfReportDataInput">
                                <button type="submit" class="btn btn-pdf" style="width: 100%;">
                                    <i class="fas fa-file-pdf"></i>
                                    Download PDF Report
                                </button>
                            </form>
                            
                            <!-- Removed the Return Home button to ensure only two aligned buttons remain -->
                        </div>
                        
                        <!-- Mobile PDF download help instructions REMOVED -->
                    </div>
                </div>
            </div>

            <script>
                // Check if we're on a mobile device - NO LONGER NEEDED FOR PDF
                // const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
                
                // Image download handler
                document.getElementById('downloadImageBtn').addEventListener('click', function() {{
                    try {{
                        const link = document.createElement('a');
                        const image = document.querySelector('.result-image');
                        link.href = image.src;
                        link.download = 'tooth-analysis-result.png';
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                    }} catch (error) {{
                        console.error('Download failed:', error);
                        alert('Failed to download image. Please try again.');
                    }}
                }});
                
                // PDF download handler with mobile support - REMOVED OLD LOGIC
                
                // New script to populate the hidden input for PDF download form
                const pdfDataForForm = {pdf_report_data_json_for_script}; 
                const pdfReportDataInputElement = document.getElementById('pdfReportDataInput');
                if (pdfReportDataInputElement) {{
                    pdfReportDataInputElement.value = JSON.stringify(pdfDataForForm);
                }} else {{
                    console.error("PDF report data input field ('pdfReportDataInput') not found.");
                }}

                // Fade in animation for the result image
                document.querySelector('.result-image').addEventListener('load', function() {{
                    this.style.animation = 'fadeIn 0.5s ease-in';
                }});
                
                // Enable PDF instructions if on mobile device - REMOVED
                // if (isMobile) {{
                // document.getElementById('pdfHelp').style.display = 'none'; // Initially hidden, shown after clicking
                // }}
            </script>
        </body>
        </html>
        """)
    except Exception as e:
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <title>Error</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
            <style>
                :root {{
                    --primary-color: #2D3250;
                    --secondary-color: #424769;
                    --accent-color: #676F9D;
                    --light-color: #F9B17A;
                    --error-color: #dc3545;
                }}
                
                body {{
                    background-color: var(--primary-color);
                    font-family: 'Poppins', sans-serif;
                    min-height: 100vh;
                    padding: 2rem 0;
                }}
                
                .card {{
                    background: rgba(255, 255, 255, 0.95);
                    border-radius: 15px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                    backdrop-filter: blur(10px);
                    border: none;
                }}
                
                .error-message {{
                    background: rgba(220, 53, 69, 0.1);
                    border: 1px solid var(--error-color);
                    border-radius: 8px;
                    padding: 1rem;
                    margin: 1rem 0;
                    color: var(--error-color);
                    font-family: 'Roboto Mono', monospace;
                }}
            </style>
            <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600&family=Roboto+Mono&display=swap" rel="stylesheet">
        </head>
        <body class="container">
            <div class="row justify-content-center">
                <div class="col-md-8">
                    <div class="card">
                        <div class="card-header bg-danger text-white py-3">
                            <i class="fas fa-exclamation-triangle me-2"></i>Error During Prediction
                        </div>
                <div class="card-body">
                            <div class="text-center mb-4">
                                <i class="fas fa-times-circle fa-3x text-danger mb-3"></i>
                                <h4>An Error Occurred</h4>
                            </div>
                            
                            <div class="error-message">
                                <pre class="mb-0">{str(e)}</pre>
                            </div>
                            
                            <div class="text-center mt-4">
                                <a href="/" class="btn btn-primary">
                                    <i class="fas fa-home me-2"></i>Return Home
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=80)

