import React, { useState } from 'react';
import {
  Container,
  Paper,
  Typography,
  Box,
  Button,
  CircularProgress,
  Alert,
  Card,
  CardContent,
  Fade,
  Slide,
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import axios from 'axios';
import './App.css';

interface OCRResult {
  filename: string;
  extracted_text: string;
  image_id: string;
  timestamp: string;
}

const App: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<OCRResult | null>(null);
  const [error, setError] = useState<string>('');

  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      if (!file.type.startsWith('image/')) {
        setError('Please select an image file');
        return;
      }
      setSelectedFile(file);
      setError('');
      
      // Create preview
      const reader = new FileReader();
      reader.onload = (e) => {
        setPreview(e.target?.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a file first');
      return;
    }

    const formData = new FormData();
    formData.append('file', selectedFile);

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const response = await axios.post(
        `${API_BASE_URL}/OCR/upload-image`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      // Handle the response - check for different possible formats
      const data = response.data;
      
      if (data.error) {
        setError(data.error || 'Failed to extract text from image');
      } else {
        setResult({
          filename: selectedFile.name,
          extracted_text: typeof data === 'string' ? data : JSON.stringify(data, null, 2),
          image_id: data.image_id || 'unknown',
          timestamp: new Date().toISOString(),
        });
      }
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const errorMessage = err.response?.data?.detail || 
                            err.response?.data?.error ||
                            err.message ||
                            'Failed to extract text from image. Make sure backend is running on http://localhost:8000';
        setError(errorMessage);
      } else {
        setError('An unexpected error occurred. Is the backend running?');
      }
      console.error('Upload error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setPreview('');
    setResult(null);
    setError('');
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        py: 6,
      }}
    >
      <Container maxWidth="lg">
        <Box sx={{ textAlign: 'center', mb: 6 }}>
          <Fade in timeout={1000}>
            <Box>
              <Typography
                variant="h2"
                component="h1"
                sx={{
                  fontWeight: 800,
                  color: 'white',
                  mb: 2,
                  textShadow: '0 4px 20px rgba(0,0,0,0.1)',
                  letterSpacing: '-1px',
                }}
              >
                ✨ OCR Text Extraction
              </Typography>
              <Typography
                variant="h6"
                sx={{
                  color: 'rgba(255,255,255,0.9)',
                  fontWeight: 300,
                  letterSpacing: '0.5px',
                }}
              >
                Upload an image and instantly extract text using AI
              </Typography>
            </Box>
          </Fade>
        </Box>

        <Slide direction="up" in timeout={1200}>
          <Paper
            elevation={20}
            sx={{
              p: 5,
              mb: 4,
              borderRadius: 4,
              background: 'linear-gradient(to bottom, #ffffff, #f8f9fa)',
              backdropFilter: 'blur(10px)',
              border: '1px solid rgba(255,255,255,0.2)',
            }}
          >
            {/* Upload Section */}
            <Box
              sx={{
                border: '3px dashed #667eea',
                borderRadius: 3,
                p: 4,
                textAlign: 'center',
                mb: 3,
                backgroundColor: '#f0f4ff',
                cursor: 'pointer',
                transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
                '&:hover': {
                  backgroundColor: '#e6edff',
                  borderColor: '#764ba2',
                  transform: 'translateY(-4px)',
                  boxShadow: '0 12px 24px rgba(102, 126, 234, 0.2)',
                },
                position: 'relative',
                overflow: 'hidden',
              }}
              component="label"
            >
              <input
                type="file"
                accept="image/*"
                onChange={handleFileSelect}
                style={{ display: 'none' }}
                disabled={loading}
              />
              <Box sx={{ position: 'relative', zIndex: 2 }}>
                <Box
                  sx={{
                    animation: 'float 3s ease-in-out infinite',
                    '@keyframes float': {
                      '0%, 100%': { transform: 'translateY(0px)' },
                      '50%': { transform: 'translateY(-10px)' },
                    },
                  }}
                >
                  <CloudUploadIcon
                    sx={{
                      fontSize: 64,
                      color: '#667eea',
                      mb: 2,
                      filter: 'drop-shadow(0 4px 8px rgba(102, 126, 234, 0.3))',
                    }}
                  />
                </Box>
                <Typography
                  variant="h5"
                  sx={{
                    mb: 1,
                    fontWeight: 700,
                    color: '#333',
                    background: 'linear-gradient(135deg, #667eea, #764ba2)',
                    backgroundClip: 'text',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                  }}
                >
                  {selectedFile ? selectedFile.name : 'Click or Drag Image Here'}
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  Supported: PNG, JPG, GIF (Max 10MB)
                </Typography>
              </Box>
            </Box>

            {/* Preview */}
            {preview && (
              <Fade in timeout={500}>
                <Box sx={{ mb: 3 }}>
                  <Typography
                    variant="subtitle1"
                    sx={{
                      mb: 2,
                      fontWeight: 600,
                      color: '#333',
                    }}
                  >
                    📷 Preview
                  </Typography>
                  <Box
                    component="img"
                    src={preview}
                    alt="Preview"
                    sx={{
                      width: '100%',
                      maxHeight: 400,
                      borderRadius: 3,
                      boxShadow: '0 10px 40px rgba(102, 126, 234, 0.3)',
                      objectFit: 'contain',
                      animation: 'slideIn 0.6s ease-out',
                      '@keyframes slideIn': {
                        '0%': { opacity: 0, transform: 'scale(0.95)' },
                        '100%': { opacity: 1, transform: 'scale(1)' },
                      },
                    }}
                  />
                </Box>
              </Fade>
            )}

            {/* Error Alert */}
            {error && (
              <Fade in timeout={300}>
                <Alert
                  severity="error"
                  sx={{
                    mb: 3,
                    borderRadius: 2,
                    background: 'linear-gradient(135deg, #ff6b6b, #ee5a6f)',
                    color: 'white',
                    border: 'none',
                    fontSize: '0.95rem',
                    fontWeight: 500,
                    '& .MuiAlert-icon': {
                      color: 'white',
                    },
                  }}
                >
                  {error}
                </Alert>
              </Fade>
            )}

            {/* Action Buttons */}
            <Box
              sx={{
                display: 'flex',
                gap: 2,
                justifyContent: 'center',
                flexWrap: 'wrap',
              }}
            >
              <Button
                variant="contained"
                size="large"
                onClick={handleUpload}
                disabled={!selectedFile || loading}
                sx={{
                  background: 'linear-gradient(135deg, #667eea, #764ba2)',
                  color: 'white',
                  fontWeight: 700,
                  fontSize: '1rem',
                  px: 4,
                  py: 1.5,
                  borderRadius: 2,
                  boxShadow: '0 8px 24px rgba(102, 126, 234, 0.4)',
                  transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                  '&:hover:not(:disabled)': {
                    transform: 'translateY(-4px)',
                    boxShadow: '0 12px 32px rgba(102, 126, 234, 0.6)',
                  },
                  '&:disabled': {
                    opacity: 0.6,
                    cursor: 'not-allowed',
                  },
                }}
              >
                {loading ? (
                  <>
                    <CircularProgress
                      size={24}
                      sx={{ mr: 1.5, color: 'inherit' }}
                    />
                    Extracting...
                  </>
                ) : (
                  '✨ Extract Text'
                )}
              </Button>
              {selectedFile && (
                <Button
                  variant="outlined"
                  size="large"
                  onClick={handleReset}
                  disabled={loading}
                  sx={{
                    borderColor: '#667eea',
                    color: '#667eea',
                    fontWeight: 700,
                    fontSize: '1rem',
                    px: 4,
                    py: 1.5,
                    borderRadius: 2,
                    border: '2px solid',
                    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                    '&:hover': {
                      borderColor: '#764ba2',
                      color: '#764ba2',
                      backgroundColor: 'rgba(102, 126, 234, 0.05)',
                    },
                  }}
                >
                  Clear
                </Button>
              )}
            </Box>
          </Paper>
        </Slide>

        {/* Results Section */}
        {result && (
          <Slide direction="up" in timeout={800}>
            <Card
              sx={{
                borderRadius: 4,
                overflow: 'hidden',
                boxShadow: '0 20px 40px rgba(102, 126, 234, 0.2)',
                background: 'linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%)',
              }}
            >
              <CardContent sx={{ p: 4 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                  <CheckCircleIcon
                    sx={{
                      fontSize: 40,
                      color: '#667eea',
                      mr: 2,
                      animation: 'scaleIn 0.5s ease-out',
                      '@keyframes scaleIn': {
                        '0%': { transform: 'scale(0)', opacity: 0 },
                        '100%': { transform: 'scale(1)', opacity: 1 },
                      },
                    }}
                  />
                  <Typography
                    variant="h5"
                    sx={{
                      fontWeight: 700,
                      background: 'linear-gradient(135deg, #667eea, #764ba2)',
                      backgroundClip: 'text',
                      WebkitBackgroundClip: 'text',
                      WebkitTextFillColor: 'transparent',
                    }}
                  >
                    Text Extraction Complete
                  </Typography>
                </Box>

                {result.image_id && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="body2" color="textSecondary">
                      <strong>Image ID:</strong> {result.image_id}
                    </Typography>
                  </Box>
                )}

                {result.timestamp && (
                  <Box sx={{ mb: 3 }}>
                    <Typography variant="body2" color="textSecondary">
                      <strong>Extracted:</strong>{' '}
                      {new Date(result.timestamp).toLocaleString()}
                    </Typography>
                  </Box>
                )}

                <Box
                  sx={{
                    background: 'linear-gradient(135deg, #f0f4ff 0%, #f8e7ff 100%)',
                    p: 3,
                    borderRadius: 2,
                    mb: 3,
                    minHeight: 120,
                    maxHeight: 350,
                    overflowY: 'auto',
                    fontFamily: "'Courier New', monospace",
                    fontSize: '0.95rem',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    color: '#333',
                    lineHeight: 1.6,
                    border: '1px solid rgba(102, 126, 234, 0.2)',
                    animation: 'fadeIn 0.6s ease-out',
                    '@keyframes fadeIn': {
                      '0%': { opacity: 0 },
                      '100%': { opacity: 1 },
                    },
                    '&::-webkit-scrollbar': {
                      width: '8px',
                    },
                    '&::-webkit-scrollbar-track': {
                      background: 'rgba(102, 126, 234, 0.1)',
                      borderRadius: '10px',
                    },
                    '&::-webkit-scrollbar-thumb': {
                      background: 'rgba(102, 126, 234, 0.3)',
                      borderRadius: '10px',
                      '&:hover': {
                        background: 'rgba(102, 126, 234, 0.5)',
                      },
                    },
                  }}
                >
                  {result.extracted_text}
                </Box>

                <Box
                  sx={{
                    display: 'flex',
                    gap: 2,
                    justifyContent: 'center',
                    flexWrap: 'wrap',
                  }}
                >
                  <Button
                    variant="contained"
                    onClick={() => {
                      navigator.clipboard.writeText(result.extracted_text);
                      alert('✅ Copied to clipboard!');
                    }}
                    sx={{
                      background: 'linear-gradient(135deg, #667eea, #764ba2)',
                      color: 'white',
                      fontWeight: 700,
                      px: 3,
                      py: 1.2,
                      borderRadius: 2,
                      boxShadow: '0 8px 24px rgba(102, 126, 234, 0.4)',
                      transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                      '&:hover': {
                        transform: 'translateY(-4px)',
                        boxShadow: '0 12px 32px rgba(102, 126, 234, 0.6)',
                      },
                    }}
                  >
                    📋 Copy Text
                  </Button>
                  <Button
                    variant="outlined"
                    onClick={handleReset}
                    sx={{
                      borderColor: '#667eea',
                      color: '#667eea',
                      fontWeight: 700,
                      px: 3,
                      py: 1.2,
                      borderRadius: 2,
                      border: '2px solid',
                      transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                      '&:hover': {
                        borderColor: '#764ba2',
                        color: '#764ba2',
                        backgroundColor: 'rgba(102, 126, 234, 0.05)',
                      },
                    }}
                  >
                    ↻ Extract Another
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Slide>
        )}
      </Container>
    </Box>
  );
};

export default App;
