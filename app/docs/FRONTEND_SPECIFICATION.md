# Frontend Specification - MAXA ML Platform Web UI

**Version**: 1.0
**Last Updated**: 2026-01-08
**Purpose**: Detailed specification for React-based web interface for ML platform

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [Design System](#design-system)
5. [Application Structure](#application-structure)
6. [Page Specifications](#page-specifications)
7. [Component Library](#component-library)
8. [State Management](#state-management)
9. [Data Flow & API Integration](#data-flow--api-integration)
10. [Real-time Features](#real-time-features)
11. [Routing & Navigation](#routing--navigation)
12. [Forms & Validation](#forms--validation)
13. [Visualizations](#visualizations)
14. [Responsive Design](#responsive-design)
15. [Accessibility](#accessibility)
16. [Performance](#performance)
17. [Testing](#testing)
18. [Deployment](#deployment)
19. [Security](#security)

---

## Overview

### Purpose

The MAXA ML Platform Web UI is a **modern React-based single-page application** that provides data scientists with a visual interface to perform all ML operations available through the MCP server. It enables users to manage datasets, run experiments, train models, perform analysis, and monitor deployments through an intuitive web interface.

### Key Goals

1. **Feature Parity**: All MCP server capabilities accessible via UI
2. **User-Friendly**: Intuitive workflows for data scientists
3. **Real-time Updates**: Live job progress, metrics, logs
4. **Collaborative**: Share experiments, models, insights
5. **Production-Ready**: Enterprise-grade UI/UX
6. **Responsive**: Works on desktop, tablet, mobile

### Target Users

- **Data Scientists**: Primary users performing experiments
- **ML Engineers**: Model deployment and monitoring
- **Data Analysts**: Statistical analysis and reporting
- **Team Leads**: Project oversight and collaboration
- **Admins**: User and system management

---

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Browser (Client)                        │
├─────────────────────────────────────────────────────────┤
│                  React Application                       │
│  ┌─────────────────────────────────────────────────┐   │
│  │           Presentation Layer                     │   │
│  │  • Pages (Dashboard, Datasets, Jobs, Models)    │   │
│  │  • Components (DataTable, JobCard, Chart)       │   │
│  │  • Layout (Header, Sidebar, Footer)             │   │
│  └────────────────┬────────────────────────────────┘   │
│  ┌────────────────▼────────────────────────────────┐   │
│  │           State Management                       │   │
│  │  • Global State (Zustand/Redux)                 │   │
│  │  • Server State (React Query)                   │   │
│  │  • Form State (React Hook Form)                 │   │
│  └────────────────┬────────────────────────────────┘   │
│  ┌────────────────▼────────────────────────────────┐   │
│  │           Service Layer                          │   │
│  │  • API Client (Axios/Fetch)                     │   │
│  │  • WebSocket Client                             │   │
│  │  • Authentication Service                       │   │
│  │  • Data Transformers                            │   │
│  └────────────────┬────────────────────────────────┘   │
└──────────────────┼──────────────────────────────────────┘
                   │
                   │ HTTP / WebSocket
                   │
┌──────────────────▼──────────────────────────────────────┐
│              FastAPI Backend                             │
│              (Port 8000)                                 │
└──────────────────────────────────────────────────────────┘
```

### Component Architecture

**Atomic Design Pattern**:
```
Atoms (Basic building blocks)
  └─> Molecules (Combinations of atoms)
      └─> Organisms (Complex components)
          └─> Templates (Page layouts)
              └─> Pages (Complete views)
```

---

## Technology Stack

### Core Framework

- **React 18+**: UI library with concurrent features
- **TypeScript**: Type-safe JavaScript
- **Vite**: Fast build tool and dev server
- **React Router v6**: Client-side routing

### State Management

- **Zustand**: Lightweight global state (auth, UI preferences)
- **React Query (TanStack Query)**: Server state management, caching
- **React Hook Form**: Form state management
- **Zod**: Schema validation for forms

### UI Component Library

**Option 1: Material-UI (MUI)**
- Comprehensive component library
- Good documentation
- Enterprise-ready
- Customizable theming

**Option 2: Ant Design**
- Data-heavy UI components
- Excellent table/form components
- Good for dashboards

**Option 3: Chakra UI**
- Modern, accessible
- Good developer experience
- Smaller bundle size

**Recommendation**: **Material-UI (MUI)** for comprehensive components and maturity

### Data Visualization

- **Recharts**: React-native charts (simple, declarative)
- **Plotly.js**: Advanced scientific visualizations
- **D3.js**: Custom visualizations (if needed)
- **React Flow**: Interactive workflow diagrams

### Real-time Communication

- **WebSocket API**: Native browser WebSocket
- **Socket.io-client** (alternative): Fallback support

### Utilities

- **Axios**: HTTP client
- **date-fns**: Date manipulation
- **lodash**: Utility functions
- **react-dropzone**: File upload
- **react-markdown**: Markdown rendering
- **Monaco Editor**: Code editor (for SQL, Python snippets)

### Development Tools

- **ESLint**: Linting
- **Prettier**: Code formatting
- **Husky**: Git hooks
- **Vitest**: Unit testing
- **Playwright**: E2E testing
- **Storybook**: Component development

---

## Design System

### Color Palette

**Primary Colors**:
```
Primary Blue: #1976D2
Secondary Teal: #00897B
Accent Orange: #FF6F00
```

**Semantic Colors**:
```
Success: #4CAF50
Warning: #FF9800
Error: #F44336
Info: #2196F3
```

**Neutral Colors**:
```
Background: #FAFAFA
Surface: #FFFFFF
Text Primary: #212121
Text Secondary: #757575
Divider: #E0E0E0
```

### Typography

**Font Family**:
- Primary: 'Inter', sans-serif
- Monospace: 'JetBrains Mono', monospace

**Type Scale**:
```
h1: 2.5rem / 40px (Page titles)
h2: 2rem / 32px (Section titles)
h3: 1.5rem / 24px (Card titles)
h4: 1.25rem / 20px (Subsections)
body1: 1rem / 16px (Regular text)
body2: 0.875rem / 14px (Secondary text)
caption: 0.75rem / 12px (Labels, hints)
```

### Spacing

**8px Grid System**:
```
xs: 4px
sm: 8px
md: 16px
lg: 24px
xl: 32px
xxl: 48px
```

### Elevation (Shadows)

```
Level 1: 0 1px 3px rgba(0,0,0,0.12)
Level 2: 0 3px 6px rgba(0,0,0,0.16)
Level 3: 0 10px 20px rgba(0,0,0,0.19)
```

### Iconography

**Icon Library**: Material Icons or Heroicons
**Icon Sizes**: 16px, 20px, 24px, 32px

---

## Application Structure

### Project Structure

```
frontend/
├── public/
│   ├── index.html
│   └── assets/
├── src/
│   ├── main.tsx                # App entry point
│   ├── App.tsx                 # Root component
│   ├── routes/                 # Route definitions
│   ├── pages/                  # Page components
│   │   ├── Dashboard/
│   │   ├── Datasets/
│   │   ├── Jobs/
│   │   ├── Models/
│   │   ├── Experiments/
│   │   └── Settings/
│   ├── components/             # Shared components
│   │   ├── common/            # Atoms & molecules
│   │   ├── layout/            # Layout components
│   │   ├── datasets/          # Dataset-specific
│   │   ├── jobs/              # Job-specific
│   │   └── visualizations/    # Charts, plots
│   ├── hooks/                  # Custom React hooks
│   ├── services/               # API clients
│   │   ├── api.ts             # Axios instance
│   │   ├── auth.ts            # Auth service
│   │   ├── datasets.ts        # Dataset endpoints
│   │   ├── jobs.ts            # Job endpoints
│   │   └── websocket.ts       # WebSocket client
│   ├── store/                  # State management
│   │   ├── authStore.ts       # Auth state
│   │   ├── uiStore.ts         # UI preferences
│   │   └── notificationStore.ts
│   ├── types/                  # TypeScript types
│   ├── utils/                  # Utility functions
│   ├── theme/                  # MUI theme config
│   ├── constants/              # Constants
│   └── tests/                  # Test files
├── .env.example
├── package.json
├── tsconfig.json
├── vite.config.ts
└── vitest.config.ts
```

---

## Page Specifications

### 1. Login Page

**Route**: `/login`

**Purpose**: User authentication

**Layout**:
```
┌─────────────────────────────────────┐
│                                     │
│        [MAXA Logo]                  │
│                                     │
│   ┌─────────────────────────┐      │
│   │  Email                   │      │
│   │  [input field]           │      │
│   │                          │      │
│   │  Password                │      │
│   │  [input field]           │      │
│   │                          │      │
│   │  [ ] Remember me         │      │
│   │                          │      │
│   │  [Login Button]          │      │
│   │                          │      │
│   │  Forgot password?        │      │
│   └─────────────────────────┘      │
│                                     │
└─────────────────────────────────────┘
```

**Features**:
- Form validation (email format, password required)
- Loading state on submission
- Error messages
- "Remember me" checkbox
- Forgot password link
- OAuth providers (Google, GitHub) - future

---

### 2. Dashboard (Home)

**Route**: `/`

**Purpose**: Overview of recent activity and key metrics

**Layout**:
```
┌────────────────────────────────────────────────────────┐
│ [Header with user menu, notifications]                │
├────┬───────────────────────────────────────────────────┤
│    │  📊 Dashboard                                     │
│ S  │  ───────────────────────────                     │
│ I  │                                                   │
│ D  │  ┌─────────┐ ┌─────────┐ ┌─────────┐            │
│ E  │  │ Datasets│ │  Jobs   │ │ Models  │            │
│ B  │  │   152   │ │   47    │ │   23    │            │
│ A  │  └─────────┘ └─────────┘ └─────────┘            │
│ R  │                                                   │
│    │  Recent Jobs                                      │
│    │  ┌──────────────────────────────────────┐       │
│    │  │ [Job Card] Training - 80% complete   │       │
│    │  │ [Job Card] HPT - Running             │       │
│    │  │ [Job Card] Inference - Completed     │       │
│    │  └──────────────────────────────────────┘       │
│    │                                                   │
│    │  Recent Experiments                              │
│    │  ┌──────────────────────────────────────┐       │
│    │  │ [Exp Card] Sales Forecasting         │       │
│    │  │ [Exp Card] Customer Segmentation     │       │
│    │  └──────────────────────────────────────┘       │
└────┴───────────────────────────────────────────────────┘
```

**Components**:
- **Metric Cards**: Dataset count, active jobs, models deployed
- **Recent Jobs List**: 5 most recent jobs with status
- **Recent Experiments**: Latest experiments with key metrics
- **Quick Actions**: Upload dataset, Start job, View models
- **Activity Feed**: Timeline of recent actions

---

### 3. Datasets Page

**Route**: `/datasets`

**Purpose**: Manage and explore datasets

**Layout**:
```
┌────────────────────────────────────────────────────────┐
│ Datasets                               [Upload Button] │
├────────────────────────────────────────────────────────┤
│                                                        │
│ [Search] [Filter] [Sort]                              │
│                                                        │
│ ┌────────────────────────────────────────────────┐   │
│ │ Name ↕ │ Rows │ Cols │ Size │ Created │ Actions│   │
│ ├────────────────────────────────────────────────┤   │
│ │ sales_2024.csv │ 10K │ 15 │ 2.3MB │ 2h ago │ ...│   │
│ │ customers.xlsx │ 5K  │ 20 │ 1.1MB │ 1d ago │ ...│   │
│ │ product_data   │ 50K │ 10 │ 5.2MB │ 3d ago │ ...│   │
│ └────────────────────────────────────────────────┘   │
│                                                        │
│ [Pagination: 1 2 3 ... 10]                            │
└────────────────────────────────────────────────────────┘
```

**Features**:
- **Upload Dataset**:
  - Drag-and-drop or file picker
  - Support CSV, Excel, Parquet
  - Progress bar during upload
  - Preview first rows before saving
- **Dataset Table**:
  - Sortable columns
  - Search by name
  - Filter by tags, date range
  - Bulk actions (delete, tag)
- **Dataset Details** (click row):
  - Metadata (name, size, created, owner)
  - Column information (name, type, nulls, unique values)
  - Preview (first 100 rows, paginated)
  - Statistics (min, max, mean, std)
  - Actions: Download, Transform, Delete

---

### 4. Dataset Detail Page

**Route**: `/datasets/:id`

**Layout**:
```
┌────────────────────────────────────────────────────────┐
│ ← Datasets / sales_2024.csv                            │
├────────────────────────────────────────────────────────┤
│ [Overview] [Preview] [Statistics] [Visualize] [Quality]│
├────────────────────────────────────────────────────────┤
│                                                        │
│ **Overview Tab**                                       │
│ Name: sales_2024.csv                                   │
│ Rows: 10,543                                          │
│ Columns: 15                                           │
│ Size: 2.3 MB                                          │
│ Created: 2 hours ago by you                           │
│ Tags: [sales] [2024] [+]                              │
│                                                        │
│ Columns:                                              │
│ ┌────────────────────────────────────────┐           │
│ │ Name │ Type │ Nulls │ Unique │ Sample  │           │
│ ├────────────────────────────────────────┤           │
│ │ date │ date │ 0%    │ 365    │ 2024-01 │           │
│ │ sales│ float│ 2%    │ 5432   │ 1234.56 │           │
│ └────────────────────────────────────────┘           │
│                                                        │
│ [Download] [Transform] [Delete]                       │
└────────────────────────────────────────────────────────┘
```

**Tabs**:

**1. Overview Tab**:
- Metadata display
- Column list with types
- Tags (editable)
- Description (editable)
- Actions

**2. Preview Tab**:
- Data table (paginated, 50 rows/page)
- Column filtering
- Row filtering
- Export visible rows

**3. Statistics Tab**:
- Summary statistics (mean, std, min, max, quartiles)
- Missing value analysis
- Correlation matrix
- Distribution histograms

**4. Visualize Tab**:
- Quick charts (histogram, scatter, bar)
- Custom visualizations
- Save charts as images

**5. Quality Tab**:
- Data quality score
- Completeness, uniqueness, validity metrics
- Outlier detection results
- Data drift analysis (vs reference dataset)

---

### 5. Jobs Page

**Route**: `/jobs`

**Purpose**: Monitor and manage ML jobs

**Layout**:
```
┌────────────────────────────────────────────────────────┐
│ Jobs                                [New Job ▼]        │
├────────────────────────────────────────────────────────┤
│ [All] [Running] [Completed] [Failed]                   │
│                                                        │
│ ┌────────────────────────────────────────────────┐   │
│ │ ⚙️ Training: XGBoost Sales Model               │   │
│ │ Status: Running (75%)                          │   │
│ │ Started: 10 minutes ago                        │   │
│ │ ████████████░░░░                               │   │
│ │ [View Details] [Cancel]                        │   │
│ ├────────────────────────────────────────────────┤   │
│ │ 🔍 HPT: RandomForest Tuning                    │   │
│ │ Status: Completed                              │   │
│ │ Duration: 2 hours 15 minutes                   │   │
│ │ Best Metric: 0.95                              │   │
│ │ [View Details] [Retry]                         │   │
│ └────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────┘
```

**Job Types**:
- Training
- Hyperparameter Tuning
- Batch Inference
- Pipeline Execution
- Feature Engineering

**Job Card Components**:
- Job type icon
- Job name (clickable to details)
- Status badge (Running, Completed, Failed, Cancelled)
- Progress bar (for running jobs)
- Duration or time remaining
- Key metrics (for completed jobs)
- Actions (View, Cancel, Retry, Delete)

---

### 6. Job Detail Page

**Route**: `/jobs/:id`

**Layout**:
```
┌────────────────────────────────────────────────────────┐
│ ← Jobs / Training: XGBoost Sales Model                │
├────────────────────────────────────────────────────────┤
│ [Overview] [Logs] [Metrics] [Config]                   │
├────────────────────────────────────────────────────────┤
│                                                        │
│ **Overview Tab**                                       │
│                                                        │
│ Status: Running                                        │
│ Progress: 75%                                          │
│ Started: 10 minutes ago                               │
│ Estimated completion: 3 minutes                        │
│                                                        │
│ ████████████████████████████░░░░░░░░                  │
│                                                        │
│ Live Metrics:                                         │
│ ┌────────────────────────────────────────┐           │
│ │ Loss: 0.234   Accuracy: 0.95           │           │
│ │ [Loss Chart Over Time]                 │           │
│ └────────────────────────────────────────┘           │
│                                                        │
│ [Cancel Job]                                          │
└────────────────────────────────────────────────────────┘
```

**Tabs**:

**1. Overview**:
- Status, progress, timing
- Live metrics (updating in real-time via WebSocket)
- Job configuration summary
- Actions (Cancel, Retry)

**2. Logs**:
- Live streaming logs (auto-scroll to bottom)
- Filter by log level (INFO, WARNING, ERROR)
- Search logs
- Download logs

**3. Metrics** (for training/HPT jobs):
- Metric charts (loss, accuracy over time/trials)
- Comparison to previous runs
- Export metrics as CSV

**4. Config**:
- Full job configuration (JSON viewer)
- Hyperparameters
- Dataset information
- Model architecture

---

### 7. Models Page

**Route**: `/models`

**Purpose**: Browse and manage registered models

**Layout**:
```
┌────────────────────────────────────────────────────────┐
│ Models                                                 │
├────────────────────────────────────────────────────────┤
│ [All] [Production] [Staging] [Archived]                │
│                                                        │
│ ┌────────────────────────────────────────────────┐   │
│ │ 🎯 Sales Forecaster                            │   │
│ │ Latest Version: v5 (Production)                │   │
│ │ Metric: RMSE 12.3                              │   │
│ │ Last Updated: 2 hours ago                      │   │
│ │ [View Details] [Deploy]                        │   │
│ ├────────────────────────────────────────────────┤   │
│ │ 👥 Customer Segmentation                       │   │
│ │ Latest Version: v3 (Staging)                   │   │
│ │ Metric: Accuracy 0.87                          │   │
│ │ Last Updated: 1 day ago                        │   │
│ │ [View Details] [Promote]                       │   │
│ └────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────┘
```

**Model Card**:
- Model name
- Latest version and stage
- Key metric
- Last updated
- Actions (View, Deploy, Promote, Archive)

---

### 8. Model Detail Page

**Route**: `/models/:name`

**Layout**:
```
┌────────────────────────────────────────────────────────┐
│ ← Models / Sales Forecaster                           │
├────────────────────────────────────────────────────────┤
│ [Overview] [Versions] [Performance] [Inference]        │
├────────────────────────────────────────────────────────┤
│                                                        │
│ **Overview Tab**                                       │
│                                                        │
│ Name: Sales Forecaster                                │
│ Description: XGBoost model for daily sales prediction │
│ Tags: [sales] [xgboost] [production]                  │
│                                                        │
│ Latest Versions:                                       │
│ • v5 (Production) - RMSE: 12.3                        │
│ • v4 (Staging) - RMSE: 13.1                           │
│ • v3 (Archived) - RMSE: 15.2                          │
│                                                        │
│ Created: 3 months ago                                 │
│ Last Updated: 2 hours ago                             │
│                                                        │
│ [Make Prediction] [Promote Version]                   │
└────────────────────────────────────────────────────────┘
```

**Tabs**:

**1. Overview**:
- Model metadata
- Version list with stages
- Quick actions

**2. Versions**:
- Detailed version table
- Metrics comparison across versions
- Promote/demote actions
- Delete version

**3. Performance**:
- Evaluation metrics
- Confusion matrix (classification)
- Feature importance
- Model comparison charts

**4. Inference**:
- Make single prediction (form input)
- Batch prediction (upload file)
- View prediction history
- Download results

---

### 9. Experiments Page

**Route**: `/experiments`

**Purpose**: Browse MLflow experiments and runs

**Layout**:
```
┌────────────────────────────────────────────────────────┐
│ Experiments                                            │
├────────────────────────────────────────────────────────┤
│                                                        │
│ ┌────────────────────────────────────────────────┐   │
│ │ 🧪 Sales Forecasting                           │   │
│ │ Runs: 47                                       │   │
│ │ Last Run: 2 hours ago                          │   │
│ │ [View Runs]                                    │   │
│ ├────────────────────────────────────────────────┤   │
│ │ 🧪 Customer Segmentation                       │   │
│ │ Runs: 23                                       │   │
│ │ Last Run: 1 day ago                            │   │
│ │ [View Runs]                                    │   │
│ └────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────┘
```

---

### 10. Experiment Detail Page

**Route**: `/experiments/:id`

**Layout**:
```
┌────────────────────────────────────────────────────────┐
│ ← Experiments / Sales Forecasting                     │
├────────────────────────────────────────────────────────┤
│ [Runs Table] [Comparison] [Visualize]                  │
├────────────────────────────────────────────────────────┤
│                                                        │
│ **Runs Table**                                         │
│ Select up to 5 runs to compare: [Compare Selected]    │
│                                                        │
│ ┌────────────────────────────────────────────────┐   │
│ │ □ │ Run │ Metrics │ Params │ Created │ Duration │   │
│ ├────────────────────────────────────────────────┤   │
│ │ □ │ run-123 │ RMSE:12.3 │ lr:0.01 │ 2h ago │ 5m │   │
│ │ □ │ run-122 │ RMSE:13.1 │ lr:0.05 │ 3h ago │ 4m │   │
│ └────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────┘
```

**Features**:
- Run table with filtering/sorting
- Multi-select runs for comparison
- Metric/parameter columns (customizable)
- Quick actions (View, Compare, Delete)

---

### 11. Run Comparison Page

**Route**: `/experiments/:id/compare?runs=run1,run2,run3`

**Layout**:
```
┌────────────────────────────────────────────────────────┐
│ Compare Runs: run-123, run-122, run-121               │
├────────────────────────────────────────────────────────┤
│                                                        │
│ Metrics Comparison:                                    │
│ ┌────────────────────────────────────────────────┐   │
│ │         │ run-123 │ run-122 │ run-121         │   │
│ │ RMSE    │ 12.3    │ 13.1    │ 14.5           │   │
│ │ MAE     │ 9.2     │ 10.1    │ 11.3           │   │
│ │ R2      │ 0.95    │ 0.93    │ 0.91           │   │
│ └────────────────────────────────────────────────┘   │
│                                                        │
│ Parameters:                                            │
│ ┌────────────────────────────────────────────────┐   │
│ │         │ run-123 │ run-122 │ run-121         │   │
│ │ lr      │ 0.01    │ 0.05    │ 0.1            │   │
│ │ n_est   │ 100     │ 100     │ 50             │   │
│ └────────────────────────────────────────────────┘   │
│                                                        │
│ [Parallel Coordinates Plot]                            │
│ [Metric History Charts]                                │
└────────────────────────────────────────────────────────┘
```

---

### 12. Statistical Analysis Page

**Route**: `/analysis`

**Purpose**: Perform statistical tests and A/B tests

**Layout**:
```
┌────────────────────────────────────────────────────────┐
│ Statistical Analysis                                   │
├────────────────────────────────────────────────────────┤
│ [Hypothesis Test] [A/B Test] [Confidence Interval]     │
├────────────────────────────────────────────────────────┤
│                                                        │
│ **Hypothesis Test**                                    │
│                                                        │
│ Dataset: [Select Dataset ▼]                           │
│ Test Type: [t-test ▼]                                 │
│ Column 1: [Select Column ▼]                           │
│ Column 2: [Select Column ▼]                           │
│ Alpha: [0.05]                                          │
│ Alternative: [two-sided ▼]                             │
│                                                        │
│ [Run Test]                                             │
│                                                        │
│ Results:                                               │
│ ┌────────────────────────────────────────┐           │
│ │ Test Statistic: 2.45                   │           │
│ │ P-value: 0.014                         │           │
│ │ Significant: Yes ✓                     │           │
│ │ Interpretation: ...                    │           │
│ └────────────────────────────────────────┘           │
└────────────────────────────────────────────────────────┘
```

---

### 13. Model Explainability Page

**Route**: `/explainability`

**Layout**:
```
┌────────────────────────────────────────────────────────┐
│ Model Explainability                                   │
├────────────────────────────────────────────────────────┤
│ [SHAP] [LIME] [Partial Dependence] [Feature Contrib]   │
├────────────────────────────────────────────────────────┤
│                                                        │
│ **SHAP Analysis**                                      │
│                                                        │
│ Model: [Select Model ▼]                               │
│ Dataset: [Select Dataset ▼]                           │
│ Plot Type: [summary ▼]                                │
│ Max Samples: [100]                                     │
│                                                        │
│ [Generate Explanation]                                 │
│                                                        │
│ Results:                                               │
│ ┌────────────────────────────────────────┐           │
│ │ [SHAP Summary Plot Image]              │           │
│ │                                        │           │
│ │ Top Features:                          │           │
│ │ 1. feature_1: 0.234                    │           │
│ │ 2. feature_2: 0.189                    │           │
│ │ ...                                    │           │
│ └────────────────────────────────────────┘           │
│                                                        │
│ [Download Plot] [Download Data]                        │
└────────────────────────────────────────────────────────┘
```

---

### 14. Settings Page

**Route**: `/settings`

**Layout**:
```
┌────────────────────────────────────────────────────────┐
│ Settings                                               │
├────────────────────────────────────────────────────────┤
│ [Profile] [Preferences] [Security] [Team] [Billing]    │
├────────────────────────────────────────────────────────┤
│                                                        │
│ **Profile Tab**                                        │
│                                                        │
│ Name: [John Doe]                                       │
│ Email: [john@example.com]                             │
│ Organization: [ACME Corp]                             │
│ Role: Data Scientist                                   │
│                                                        │
│ [Save Changes]                                         │
└────────────────────────────────────────────────────────┘
```

---

## Component Library

### Common Components

**1. DataTable**:
```tsx
<DataTable
  columns={columns}
  data={data}
  sortable
  filterable
  pagination
  onRowClick={(row) => navigate(`/datasets/${row.id}`)}
/>
```

**2. JobCard**:
```tsx
<JobCard
  job={job}
  onCancel={handleCancel}
  onRetry={handleRetry}
  showProgress
/>
```

**3. MetricCard**:
```tsx
<MetricCard
  title="Total Datasets"
  value={152}
  icon={<DatabaseIcon />}
  trend="+12%"
  trendDirection="up"
/>
```

**4. StatusBadge**:
```tsx
<StatusBadge
  status="running"
  text="Running"
/>
```

**5. FileUpload**:
```tsx
<FileUpload
  accept={['.csv', '.xlsx', '.parquet']}
  maxSize={100 * 1024 * 1024} // 100MB
  onUpload={handleUpload}
  multiple={false}
/>
```

**6. Chart Components**:
```tsx
<LineChart data={metricsData} xKey="step" yKey="loss" />
<BarChart data={featureImportance} xKey="feature" yKey="importance" />
<ScatterPlot data={correlationData} xKey="var1" yKey="var2" />
```

---

## State Management

### Global State (Zustand)

**Auth Store**:
```typescript
interface AuthState {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<void>;
}
```

**UI Store**:
```typescript
interface UIState {
  theme: 'light' | 'dark';
  sidebarOpen: boolean;
  notifications: Notification[];
  addNotification: (notification: Notification) => void;
  removeNotification: (id: string) => void;
}
```

### Server State (React Query)

**Dataset Queries**:
```typescript
// Fetch datasets
const { data, isLoading } = useQuery({
  queryKey: ['datasets'],
  queryFn: fetchDatasets
});

// Fetch single dataset
const { data: dataset } = useQuery({
  queryKey: ['datasets', id],
  queryFn: () => fetchDataset(id)
});

// Upload dataset mutation
const uploadMutation = useMutation({
  mutationFn: uploadDataset,
  onSuccess: () => {
    queryClient.invalidateQueries(['datasets']);
  }
});
```

---

## Data Flow & API Integration

### API Client Setup

```typescript
// src/services/api.ts
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 30000,
});

// Request interceptor (add auth token)
api.interceptors.request.use((config) => {
  const token = authStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor (handle errors)
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Token expired, try refresh
      await authStore.getState().refreshToken();
      return api.request(error.config);
    }
    return Promise.reject(error);
  }
);
```

---

## Real-time Features

### WebSocket Integration

```typescript
// src/services/websocket.ts
class WebSocketClient {
  private ws: WebSocket | null = null;
  private listeners: Map<string, Set<Function>> = new Map();

  connect(token: string) {
    this.ws = new WebSocket(`${WS_URL}?token=${token}`);

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.emit(message.event, message.data);
    };
  }

  subscribe(event: string, callback: Function) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback);

    // Send subscribe message to server
    this.send({ action: 'subscribe', event });
  }

  emit(event: string, data: any) {
    this.listeners.get(event)?.forEach(cb => cb(data));
  }
}
```

**Usage in Component**:
```tsx
function JobDetailPage({ jobId }) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const ws = getWebSocketClient();

    ws.subscribe('job:progress', (data) => {
      if (data.job_id === jobId) {
        setProgress(data.progress);
      }
    });

    return () => ws.unsubscribe('job:progress');
  }, [jobId]);

  return <ProgressBar value={progress} />;
}
```

---

## Routing & Navigation

### Route Configuration

```typescript
// src/routes/index.tsx
const routes = [
  {
    path: '/',
    element: <AuthLayout />,
    children: [
      { path: 'login', element: <LoginPage /> },
      { path: 'signup', element: <SignupPage /> },
    ]
  },
  {
    path: '/',
    element: <ProtectedLayout />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'datasets', element: <DatasetsPage /> },
      { path: 'datasets/:id', element: <DatasetDetailPage /> },
      { path: 'jobs', element: <JobsPage /> },
      { path: 'jobs/:id', element: <JobDetailPage /> },
      { path: 'models', element: <ModelsPage /> },
      { path: 'models/:name', element: <ModelDetailPage /> },
      { path: 'experiments', element: <ExperimentsPage /> },
      { path: 'experiments/:id', element: <ExperimentDetailPage /> },
      { path: 'analysis', element: <AnalysisPage /> },
      { path: 'explainability', element: <ExplainabilityPage /> },
      { path: 'settings', element: <SettingsPage /> },
    ]
  }
];
```

---

## Forms & Validation

### Form Example (Job Submission)

```tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const trainingJobSchema = z.object({
  dataset_id: z.string().min(1, 'Dataset is required'),
  model_type: z.enum(['xgboost', 'random_forest', 'linear']),
  target_column: z.string().min(1),
  feature_columns: z.array(z.string()).min(1),
  hyperparameters: z.record(z.any()),
});

function TrainingJobForm() {
  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(trainingJobSchema)
  });

  const onSubmit = (data) => {
    submitTrainingJob(data);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <TextField
        {...register('target_column')}
        error={!!errors.target_column}
        helperText={errors.target_column?.message}
      />
      <Button type="submit">Submit Job</Button>
    </form>
  );
}
```

---

## Visualizations

### Chart Components

**Recharts Integration**:
```tsx
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend } from 'recharts';

function MetricsChart({ data }) {
  return (
    <LineChart width={600} height={300} data={data}>
      <XAxis dataKey="step" />
      <YAxis />
      <Tooltip />
      <Legend />
      <Line type="monotone" dataKey="loss" stroke="#8884d8" />
      <Line type="monotone" dataKey="accuracy" stroke="#82ca9d" />
    </LineChart>
  );
}
```

**Plotly for Advanced Viz**:
```tsx
import Plot from 'react-plotly.js';

function ConfusionMatrixPlot({ matrix }) {
  return (
    <Plot
      data={[{
        z: matrix,
        type: 'heatmap',
        colorscale: 'Viridis'
      }]}
      layout={{
        title: 'Confusion Matrix',
        xaxis: { title: 'Predicted' },
        yaxis: { title: 'Actual' }
      }}
    />
  );
}
```

---

## Responsive Design

### Breakpoints

```typescript
const breakpoints = {
  xs: '0px',
  sm: '600px',
  md: '900px',
  lg: '1200px',
  xl: '1536px'
};
```

### Mobile Optimizations

- Collapsible sidebar on mobile
- Stack cards vertically on small screens
- Touch-friendly buttons (min 44px)
- Responsive tables (horizontal scroll or card layout)

---

## Accessibility

### Standards

- **WCAG 2.1 Level AA** compliance
- Keyboard navigation
- Screen reader support
- Focus indicators
- ARIA labels

### Implementation

```tsx
// Accessible button
<Button
  aria-label="Upload dataset"
  aria-describedby="upload-help"
>
  Upload
</Button>

// Skip link
<a href="#main-content" className="skip-link">
  Skip to main content
</a>

// Form labels
<label htmlFor="dataset-name">Dataset Name</label>
<input id="dataset-name" />
```

---

## Performance

### Optimization Techniques

1. **Code Splitting**: Lazy load routes
2. **Image Optimization**: Use WebP, lazy loading
3. **Memoization**: React.memo, useMemo, useCallback
4. **Virtual Scrolling**: For large lists (react-window)
5. **Debouncing**: Search inputs
6. **Caching**: React Query automatic caching
7. **Bundle Size**: Tree shaking, analyze with vite-bundle-visualizer

---

## Testing

### Unit Tests (Vitest)

```typescript
import { render, screen } from '@testing-library/react';
import { JobCard } from './JobCard';

test('renders job card with status', () => {
  const job = { id: '1', name: 'Test Job', status: 'running' };
  render(<JobCard job={job} />);
  expect(screen.getByText('Test Job')).toBeInTheDocument();
  expect(screen.getByText('Running')).toBeInTheDocument();
});
```

### E2E Tests (Playwright)

```typescript
test('upload dataset flow', async ({ page }) => {
  await page.goto('/datasets');
  await page.click('text=Upload');
  await page.setInputFiles('input[type=file]', 'test.csv');
  await page.fill('input[name=name]', 'Test Dataset');
  await page.click('text=Submit');
  await expect(page.locator('text=Test Dataset')).toBeVisible();
});
```

---

## Deployment

### Build Configuration

```typescript
// vite.config.ts
export default defineConfig({
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          mui: ['@mui/material', '@mui/icons-material'],
        }
      }
    }
  }
});
```

### Docker Configuration

```dockerfile
# Dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Environment Variables

```bash
# .env.production
VITE_API_URL=https://api.maxa-ml.com
VITE_WS_URL=wss://api.maxa-ml.com/ws
VITE_SENTRY_DSN=...
```

---

## Security

### Best Practices

1. **XSS Prevention**: Sanitize user input, use React's built-in escaping
2. **CSRF Protection**: Use CSRF tokens for state-changing operations
3. **Content Security Policy**: Restrict resource loading
4. **Secure Storage**: Store tokens in httpOnly cookies or secure localStorage
5. **Input Validation**: Client-side + server-side validation
6. **Dependency Scanning**: Regular npm audit

---

**End of Frontend Specification**
