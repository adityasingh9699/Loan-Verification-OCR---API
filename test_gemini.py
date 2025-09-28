#!/usr/bin/env python3
"""
Test script to verify Gemini service configuration and model availability
"""

import os
import sys
from dotenv import load_dotenv

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

# Load environment variables
load_dotenv()

def test_gemini_service():
    """Test the Gemini service initialization and model availability"""
    try:
        from app.services.gemini_service import gemini_ocr
        from app.core.config import settings
        
        print("🔍 Testing Gemini Service Configuration")
        print("=" * 50)
        
        # Check API key
        if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your_gemini_api_key_here":
            print("❌ Gemini API key not configured")
            print("Please set GEMINI_API_KEY in your .env file")
            return False
        
        print(f"✅ API Key configured: {settings.GEMINI_API_KEY[:10]}...")
        
        # Check model initialization
        if gemini_ocr.model is None:
            print("❌ Gemini model not initialized")
            return False
        
        current_model = gemini_ocr.get_current_model_name()
        print(f"✅ Model initialized: {current_model}")
        
        # Show model capabilities
        if '2.5' in current_model:
            print("🚀 Using latest Gemini 2.5 model with enhanced capabilities")
            print("   - Advanced reasoning and multimodal processing")
            print("   - Improved coding and STEM performance")
            print("   - Enhanced document analysis capabilities")
        elif '2.0' in current_model:
            print("⚡ Using Gemini 2.0 model with improved performance")
            print("   - Better accuracy and speed")
            print("   - Enhanced multimodal understanding")
        elif '1.5' in current_model:
            print("✅ Using stable Gemini 1.5 model")
            print("   - Reliable and well-tested")
        else:
            print("📦 Using legacy Gemini model")
        
        # Test model availability
        try:
            import google.generativeai as genai
            available_models = list(genai.list_models())
            print(f"\n📋 Available models: {[model.name for model in available_models]}")
            
            # Check if our model is in the available models
            model_names = [model.name for model in available_models]
            if current_model in model_names:
                print(f"✅ Current model '{current_model}' is available")
            else:
                print(f"⚠️  Current model '{current_model}' not found in available models")
                print("Available models:", model_names)
                
        except Exception as e:
            print(f"⚠️  Could not list available models: {e}")
        
        print("\n🎉 Gemini service is properly configured!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing Gemini service: {e}")
        return False

def test_health_endpoint():
    """Test the health endpoint"""
    try:
        import requests
        import time
        
        print("\n🏥 Testing Health Endpoint")
        print("=" * 50)
        
        # Wait a moment for the server to start
        time.sleep(2)
        
        response = requests.get("http://localhost:8000/health", timeout=10)
        
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Health endpoint responding: {health_data}")
            return True
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing health endpoint: {e}")
        return False

def show_model_benefits():
    """Show the benefits of using newer Gemini models"""
    print("\n🌟 Gemini Model Benefits")
    print("=" * 50)
    print("🚀 Gemini 2.5 Series:")
    print("   - Latest and most advanced models")
    print("   - Enhanced reasoning capabilities")
    print("   - Better multimodal processing")
    print("   - Improved accuracy for complex documents")
    print("   - Faster processing times")
    
    print("\n⚡ Gemini 2.0 Series:")
    print("   - Significant performance improvements")
    print("   - Better understanding of financial documents")
    print("   - Enhanced OCR accuracy")
    print("   - Improved error handling")
    
    print("\n✅ Gemini 1.5 Series:")
    print("   - Stable and reliable")
    print("   - Good performance for most use cases")
    print("   - Well-tested in production")

if __name__ == "__main__":
    print("🚀 Starting Gemini Service Test")
    print("=" * 50)
    
    # Show model benefits
    show_model_benefits()
    
    # Test Gemini service
    gemini_ok = test_gemini_service()
    
    # Test health endpoint (if server is running)
    health_ok = test_health_endpoint()
    
    print("\n📊 Test Results")
    print("=" * 50)
    print(f"Gemini Service: {'✅ PASS' if gemini_ok else '❌ FAIL'}")
    print(f"Health Endpoint: {'✅ PASS' if health_ok else '❌ FAIL'}")
    
    if gemini_ok and health_ok:
        print("\n🎉 All tests passed! Your OCR service is ready to use.")
    else:
        print("\n⚠️  Some tests failed. Please check the configuration.")
        sys.exit(1)
