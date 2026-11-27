# OCR Frontend - React with Material UI

A modern React frontend for the OCR text extraction API built with Vite and Material UI.

## Features

- 📸 Image upload with preview
- 🔤 Automatic text extraction from images
- 📋 Copy extracted text to clipboard
- 🎨 Clean, responsive UI with Material Design
- ⚡ Built with Vite for fast development

## Quick Start

### Prerequisites
- Node.js 16+ and npm

### Installation

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Configure the backend API URL (optional):
```bash
# Edit .env file
VITE_API_URL=http://localhost:8000
```

3. Start the development server:
```bash
npm run dev
```

The app will open at `http://localhost:5173`

### Build for Production

```bash
npm run build
```

Output will be in the `dist/` folder.

## Usage

1. Click on the upload area to select an image or drag and drop
2. Click "Extract Text" to send the image to the OCR API
3. View the extracted text in the results panel
4. Click "Copy Text" to copy to clipboard or "Extract Another" to process more images

## API Endpoints Used

- **POST /OCR/extract-text** - Upload image and extract text

The frontend expects the backend API to be running on `http://localhost:8000` by default.

## Project Structure

```
frontend/
├── src/
│   ├── App.tsx          # Main React component
│   ├── App.css          # Styles
│   ├── main.tsx         # App entry point
│   └── main.ts          # Original template
├── index.html           # HTML template
├── package.json         # Dependencies
├── vite.config.ts       # Vite configuration
├── tsconfig.json        # TypeScript configuration
└── .env                 # Environment variables
```

## Technologies

- **React 19** - UI library
- **Vite 8** - Build tool
- **Material UI (MUI)** - Component library
- **Axios** - HTTP client
- **TypeScript** - Type safety

## Development

### Run Development Server
```bash
npm run dev
```

### Build
```bash
npm run build
```

### Preview Production Build
```bash
npm run preview
```

## Environment Variables

Create a `.env` file in the frontend directory:

```env
VITE_API_URL=http://localhost:8000
```

## Notes

- The backend must have CORS enabled for the frontend to work
- Make sure the OCR API is running on port 8000 before using the frontend
- For production deployment, build the app and serve the `dist/` folder
