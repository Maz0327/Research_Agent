# Research Agent Frontend

Next.js frontend for the Research Agent application.

## Setup

### Install Dependencies

```bash
npm install
```

### Configure Environment

Copy `.env.example` to `.env.local` and configure:

```bash
cp .env.example .env.local
```

Set `NEXT_PUBLIC_API_URL` to your backend API URL (defaults to `http://localhost:8000` if not set).

### Development

Run the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Build

Build for production:

```bash
npm run build
```

Start production server:

```bash
npm start
```

## Features

- **Research Job Form**: Submit research prompts with pipeline selection (Quick/Full)
- **Job Status Display**: View job status after submission
- **TypeScript**: Full type safety
- **ESLint + Prettier**: Code quality and formatting
- **Tailwind CSS**: Utility-first CSS framework

## Project Structure

```
frontend/
├── pages/
│   ├── _app.tsx          # Next.js app wrapper
│   └── index.tsx         # Main form page
├── styles/
│   └── globals.css       # Global styles and Tailwind imports
├── next.config.js        # Next.js configuration
├── tsconfig.json         # TypeScript configuration
├── tailwind.config.js    # Tailwind CSS configuration
└── package.json          # Dependencies and scripts
```

## API Integration

The frontend communicates with the backend API at `/jobs` endpoint:

- **POST /jobs**: Create a new research job
- **GET /jobs/{job_id}**: Get job status (future enhancement)

The form currently sends:
- `topic`: Research prompt text

The pipeline selection (Quick/Full) is included in the UI but not yet sent to the backend (will be implemented in future updates).












