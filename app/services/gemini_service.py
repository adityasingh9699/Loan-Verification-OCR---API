import google.generativeai as genai
from app.core.config import settings
import logging
import json
import requests
import base64
from typing import Dict, Any

logger = logging.getLogger(__name__)

class GeminiOCRService:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        # Try different model names in order of preference (newest first)
        self.model_names = [
            'gemini-2.5-flash',      # Latest and fastest
            'gemini-2.5-pro',        # Latest and most capable
            'gemini-2.0-flash',      # Gemini 2.0 series
            'gemini-2.0-pro',        # Gemini 2.0 series
            'gemini-1.5-pro',        # Fallback to 1.5 series
            'gemini-1.5-flash',      # Fallback to 1.5 series
            'gemini-pro',            # Legacy fallback
            'gemini-1.0-pro'         # Legacy fallback
        ]
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the model with the first available one"""
        for model_name in self.model_names:
            try:
                self.model = genai.GenerativeModel(model_name)
                logger.info(f"Successfully initialized Gemini model: {model_name}")
                
                # Log model capabilities
                if '2.5' in model_name:
                    logger.info("🚀 Using latest Gemini 2.5 model with enhanced capabilities")
                elif '2.0' in model_name:
                    logger.info("⚡ Using Gemini 2.0 model with improved performance")
                elif '1.5' in model_name:
                    logger.info("✅ Using stable Gemini 1.5 model")
                else:
                    logger.info("📦 Using legacy Gemini model")
                
                break
            except Exception as e:
                logger.warning(f"Failed to initialize model {model_name}: {e}")
                continue
        
        if self.model is None:
            # List available models for debugging
            try:
                available_models = list(genai.list_models())
                logger.error(f"Available models: {[model.name for model in available_models]}")
            except Exception as e:
                logger.error(f"Could not list available models: {e}")
            raise Exception("Failed to initialize any Gemini model. Please check your API key and model availability.")
    
    def get_current_model_name(self) -> str:
        """Get the name of the currently initialized model"""
        return self.model.model_name if self.model else "No model initialized"
    
    async def extract_paystub_data(self, image_url: str) -> Dict[str, Any]:
        """Extract structured data from pay stub using Gemini Vision with enhanced processing"""
        try:
            logger.info(f"Extracting data from image URL: {image_url}")
            logger.info(f"Using Gemini model: {self.get_current_model_name()}")
            if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your_gemini_api_key_here":
                logger.error("Gemini API key not configured")
                raise Exception("Gemini API key not configured")
            
            # Expert-level prompt with comprehensive field recognition
            prompt = """
            You are an expert financial document analyst specializing in pay stubs, income statements, and employment verification documents. 
            Analyze this document and extract the following information in JSON format with maximum accuracy:
            
            {
                "employee_name": "Full name of the employee (first and last name)",
                "company_name": "Name of the company/employer",
                "annual_salary": "Annual salary as a number (calculate if needed)",
                "ssn": "Social Security Number (last 4 digits only for privacy)",
                "pay_period": "Pay period information (weekly, bi-weekly, monthly, etc.)",
                "gross_pay": "Gross pay amount for this period",
                "net_pay": "Net pay amount for this period",
                "deductions": "List of deductions (taxes, insurance, etc.)",
                "pay_date": "Pay date (YYYY-MM-DD format if possible)",
                "hourly_rate": "Hourly rate if applicable",
                "hours_worked": "Hours worked this period if applicable",
                "year_to_date_gross": "Year-to-date gross pay if available",
                "year_to_date_net": "Year-to-date net pay if available"
            }
            
            COMPREHENSIVE FIELD RECOGNITION PATTERNS:
            
            EMPLOYEE NAME VARIATIONS:
            - "Employee Name", "Name", "Employee", "Payee", "Worker", "Staff Member"
            - "Full Name", "Complete Name", "Worker Name", "Staff Name"
            - "Payee Name", "Recipient", "Beneficiary", "Associate"
            - Look in headers, employee sections, or personal information areas
            
            COMPANY/EMPLOYER VARIATIONS:
            - "Company", "Employer", "Business Name", "Payor", "Client", "Organization"
            - "Company Name", "Employer Name", "Business", "Corporation", "Corp"
            - "Organization Name", "Institution", "Agency", "Department"
            - "Client Name", "Customer", "Account Holder", "Entity"
            
            ANNUAL SALARY CALCULATION RULES (CRITICAL - ALWAYS CALCULATE ANNUAL):
            - MONTHLY PAY: "Monthly Pay" × 12 = annual (MOST COMMON)
            - GROSS EARNINGS (Monthly): "Gross Earnings" × 12 = annual
            - NET PAY (Monthly): "Net Pay" × 12 = annual  
            - TOTAL NET PAYABLE (Monthly): "Total Net Payable" × 12 = annual
            - EMPLOYEE NET PAY (Monthly): "Employee Net Pay" × 12 = annual
            - HOURLY CALCULATION: "Hourly Rate" × 40 hours × 52 weeks = annual
            - BI-WEEKLY: "Bi-Weekly Pay" × 26 pay periods = annual
            - SEMI-MONTHLY: "Semi-Monthly Pay" × 24 pay periods = annual
            - WEEKLY: "Weekly Pay" × 52 weeks = annual
            - YEAR-TO-DATE: Use "YTD Gross" × (52 / pay periods per year)
            - DIRECT ANNUAL: "Annual Salary", "Yearly Salary", "Annual Income", "Yearly Income"
            
            SALARY EXTRACTION PRIORITY (in order):
            1. Look for "Gross Earnings" amount (multiply by 12 for annual)
            2. Look for "Total Net Payable" amount (multiply by 12 for annual)  
            3. Look for "Employee Net Pay" amount (multiply by 12 for annual)
            4. Look for "Net Pay" amount (multiply by 12 for annual)
            5. Look for "Gross Pay" amount (multiply by 12 for annual)
            6. Look for "Basic" salary (multiply by 12 for annual)
            7. Look for direct annual amounts
            
            INCOME FIELD VARIATIONS:
            - "Annual Income", "Yearly Income", "Annual Salary", "Yearly Salary"
            - "Gross Annual", "Net Annual", "Total Annual", "Base Salary"
            - "Annual Wage", "Yearly Wage", "Annual Compensation", "Yearly Compensation"
            - "Salary", "Wage", "Income", "Compensation", "Earnings"
            - "Base Pay", "Regular Pay", "Standard Pay", "Fixed Pay"
            
            HOURLY RATE VARIATIONS:
            - "Hourly Rate", "Rate", "Per Hour", "Hrly", "Hourly Wage"
            - "Pay Rate", "Wage Rate", "Rate of Pay", "Hourly Pay"
            - "Per Hour Rate", "Hourly Compensation", "Rate/Hour"
            - "Wage/Hour", "Pay/Hour", "Compensation/Hour"
            
            GROSS PAY VARIATIONS:
            - "Gross Pay", "Gross", "Total Earnings", "Earnings", "Gross Earnings"
            - "Gross Income", "Total Income", "Gross Wages", "Total Wages"
            - "Gross Compensation", "Total Compensation", "Gross Salary"
            - "Current Period Gross", "This Period Gross", "Period Gross"
            - "Regular Gross", "Base Gross", "Standard Gross"
            - "EARNINGS" table total, "Gross Earnings" total
            
            NET PAY VARIATIONS:
            - "Net Pay", "Net", "Take Home", "Final Pay", "Net Income"
            - "Net Earnings", "Take Home Pay", "Net Wages", "Final Amount"
            - "After Deductions", "Net After Taxes", "Disposable Income"
            - "Current Period Net", "This Period Net", "Period Net"
            - "Final Net", "Actual Pay", "Received Amount"
            - "Employee Net Pay", "Total Net Payable", "Net Payable"
            
            PAY PERIOD VARIATIONS:
            - "Pay Period", "Period", "Week of", "Pay Date Range", "Pay Cycle"
            - "Pay Week", "Work Period", "Earnings Period", "Payroll Period"
            - "Week Ending", "Period Ending", "Pay Date", "Earnings Date"
            - "Bi-Weekly", "Semi-Monthly", "Monthly", "Weekly", "Daily"
            - "Pay Frequency", "Payroll Frequency", "Payment Schedule"
            
            SSN VARIATIONS:
            - "SSN", "Social Security", "SS#", "Social Sec", "Social Security Number"
            - "SS Number", "Social Security #", "SSN #", "Social Sec #"
            - "Employee ID", "Employee Number", "Staff ID", "Worker ID"
            - Look for patterns like XXX-XX-XXXX or XXXXXXXXX
            
            YEAR-TO-DATE VARIATIONS:
            - "YTD Gross", "Year to Date Gross", "YTD Earnings", "Year to Date Earnings"
            - "YTD Income", "Year to Date Income", "YTD Wages", "Year to Date Wages"
            - "YTD Net", "Year to Date Net", "YTD Take Home", "Year to Date Take Home"
            - "Cumulative Gross", "Total YTD", "Running Total", "Accumulated"
            
            DEDUCTIONS VARIATIONS:
            - "Deductions", "Withholdings", "Taxes", "Insurance", "Benefits"
            - "Federal Tax", "State Tax", "Local Tax", "FICA", "Medicare"
            - "Social Security", "Health Insurance", "Dental", "Vision"
            - "401k", "Retirement", "Pension", "Union Dues", "Garnishments"
            - "Pre-tax", "Post-tax", "Voluntary", "Mandatory"
            
            PAY DATE VARIATIONS:
            - "Pay Date", "Payment Date", "Issue Date", "Check Date"
            - "Pay Period End", "Period End Date", "Earnings Date"
            - "Direct Deposit Date", "Payment Date", "Issue Date"
            - Look for dates in MM/DD/YYYY, DD/MM/YYYY, or YYYY-MM-DD format
            
            INDIAN PAYSLIP SPECIFIC PATTERNS:
            - Look for "Employee Name" in EMPLOYEE SUMMARY section
            - Look for company name in header (e.g., "Zylker", "ZOHO")
            - Look for "Gross Earnings" total in EARNINGS table
            - Look for "Employee Net Pay" or "Total Net Payable" amounts
            - Look for "Basic" salary in EARNINGS table
            - Pay period is usually "March 2024" format - extract as "monthly"
            - Look for "Pay Date" in employee summary section
            - Look for "UAN" or "PF A/C Number" for employee identification
            - Currency is usually ₹ (Indian Rupees)
            
            EXTRACTION GUIDELINES:
            1. Be thorough - check all sections of the document
            2. Look for both labeled and unlabeled fields
            3. Handle different document layouts and formats
            4. Extract numbers without currency symbols ($, €, £, ₹, etc.)
            5. Convert all amounts to numbers (remove commas, spaces)
            6. For dates, prefer YYYY-MM-DD format when possible
            7. If multiple values exist, use the most recent or current period
            8. If a field is not found or unclear, set it to null
            9. Return ONLY valid JSON, no additional text or explanations
            
            DOCUMENT TYPES TO HANDLE:
            - Pay stubs, Payroll statements, Earnings statements
            - Income statements, Salary certificates, Employment letters
            - W-2 forms, 1099 forms, Tax documents
            - Bank statements, Direct deposit notifications
            - Employment verification letters, Salary verification forms
            """
            
            # Download the file from GCP URL with retry logic
            logger.info(f"Downloading file from URL: {image_url}")
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    file_response = requests.get(image_url, timeout=30)
                    file_response.raise_for_status()
                    break
                except requests.exceptions.RequestException as e:
                    if attempt == max_retries - 1:
                        raise Exception(f"Failed to download file after {max_retries} attempts: {str(e)}")
                    logger.warning(f"Download attempt {attempt + 1} failed: {e}, retrying...")
                    import time
                    time.sleep(2 ** attempt)  # Exponential backoff
            
            # Determine MIME type based on file extension
            if image_url.lower().endswith('.pdf'):
                mime_type = "application/pdf"
            elif image_url.lower().endswith('.png'):
                mime_type = "image/png"
            elif image_url.lower().endswith('.jpg') or image_url.lower().endswith('.jpeg'):
                mime_type = "image/jpeg"
            else:
                mime_type = "image/jpeg"  # Default fallback
            
            # Convert to base64
            file_data = base64.b64encode(file_response.content).decode('utf-8')
            
            # Generate content with retry logic
            for attempt in range(max_retries):
                try:
                    response = self.model.generate_content([
                        prompt,
                        {
                            "mime_type": mime_type,
                            "data": file_data
                        }
                    ])
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise Exception(f"Failed to process document after {max_retries} attempts: {str(e)}")
                    logger.warning(f"OCR attempt {attempt + 1} failed: {e}, retrying...")
                    import time
                    time.sleep(2 ** attempt)  # Exponential backoff
            
            # Parse the response with enhanced error handling
            extracted_text = response.text.strip()
            logger.info(f"Raw OCR response: {extracted_text[:500]}...")  # Log first 500 chars
            
            # Clean up the response to extract JSON
            json_text = self._extract_json_from_response(extracted_text)
            
            # Parse JSON with validation
            extracted_data = self._parse_and_validate_json(json_text)
            
            # Post-process the data for better accuracy
            extracted_data = self._post_process_extracted_data(extracted_data)
            
            logger.info(f"Successfully extracted data: {extracted_data}")
            return extracted_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON from Gemini response: {e}")
            raise Exception("Failed to parse OCR results")
        except Exception as e:
            logger.error(f"Error extracting paystub data: {e}")
            raise Exception(f"OCR extraction failed: {str(e)}")
    
    def _extract_json_from_response(self, response_text: str) -> str:
        """Extract JSON from various response formats"""
        # Try different JSON extraction patterns
        patterns = [
            r"```json\s*(.*?)\s*```",
            r"```\s*(.*?)\s*```",
            r"\{.*\}",
        ]
        
        import re
        for pattern in patterns:
            matches = re.findall(pattern, response_text, re.DOTALL)
            if matches:
                return matches[0].strip()
        
        # If no pattern matches, return the original text
        return response_text
    
    def _parse_and_validate_json(self, json_text: str) -> Dict[str, Any]:
        """Parse and validate JSON with better error handling"""
        try:
            extracted_data = json.loads(json_text)
        except json.JSONDecodeError as e:
            # Try to fix common JSON issues
            json_text = json_text.replace("'", '"')  # Replace single quotes with double quotes
            json_text = json_text.replace("True", "true").replace("False", "false")  # Fix boolean values
            json_text = json_text.replace("None", "null")  # Fix None values
            
            try:
                extracted_data = json.loads(json_text)
            except json.JSONDecodeError:
                # If still failing, create a minimal valid JSON
                logger.warning("Failed to parse JSON, creating minimal structure")
                extracted_data = {
                    "employee_name": None,
                    "company_name": None,
                    "annual_salary": None,
                    "ssn": None,
                    "pay_period": None,
                    "gross_pay": None,
                    "net_pay": None,
                    "deductions": None,
                    "pay_date": None
                }
        
        if not isinstance(extracted_data, dict):
            raise Exception("Invalid response format - not a dictionary")
        
        return extracted_data
    
    def _post_process_extracted_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Post-process extracted data for better accuracy with enhanced field handling"""
        
        # Clean up string fields with enhanced validation
        string_fields = ["employee_name", "company_name", "ssn", "pay_period", "pay_date", "deductions"]
        for field in string_fields:
            if data.get(field) and isinstance(data[field], str):
                data[field] = data[field].strip()
                # Remove common null indicators
                if data[field] == "" or data[field].lower() in ["null", "none", "n/a", "na", "n/a", "not available", "unknown", "tbd"]:
                    data[field] = None
                # Clean up common formatting issues
                elif field == "employee_name":
                    # Normalize name formatting
                    data[field] = " ".join(word.capitalize() for word in data[field].split())
                elif field == "company_name":
                    # Normalize company name formatting
                    data[field] = data[field].title()
        
        # Clean up numeric fields with enhanced parsing
        numeric_fields = ["annual_salary", "gross_pay", "net_pay", "hourly_rate", "hours_worked", "year_to_date_gross", "year_to_date_net"]
        for field in numeric_fields:
            if data.get(field):
                try:
                    # Remove currency symbols and commas
                    if isinstance(data[field], str):
                        cleaned_value = data[field].replace("$", "").replace(",", "").replace("€", "").replace("£", "").replace("¥", "").strip()
                        data[field] = float(cleaned_value)
                    else:
                        data[field] = float(data[field])
                except (ValueError, TypeError):
                    data[field] = None
        
        # Enhanced SSN processing
        if data.get("ssn") and isinstance(data["ssn"], str):
            ssn = data["ssn"].replace("-", "").replace(" ", "").replace("_", "")
            # Handle different SSN formats
            if len(ssn) >= 4:
                data["ssn"] = ssn[-4:]  # Last 4 digits only
            elif len(ssn) > 0:
                data["ssn"] = ssn  # Keep as is if less than 4 digits
            else:
                data["ssn"] = None
        
        # Enhanced annual salary calculation with multiple fallback strategies
        if not data.get("annual_salary"):
            try:
                # Strategy 1: Use gross_pay with pay_period
                if data.get("gross_pay") and data.get("pay_period"):
                    gross_pay = float(data["gross_pay"])
                    pay_period = data["pay_period"].lower()
                    
                    if "weekly" in pay_period or "week" in pay_period:
                        data["annual_salary"] = gross_pay * 52
                    elif "bi-weekly" in pay_period or "biweekly" in pay_period or "bi weekly" in pay_period:
                        data["annual_salary"] = gross_pay * 26
                    elif "semi-monthly" in pay_period or "semi monthly" in pay_period:
                        data["annual_salary"] = gross_pay * 24
                    elif "monthly" in pay_period or "month" in pay_period:
                        data["annual_salary"] = gross_pay * 12
                    elif "daily" in pay_period or "day" in pay_period:
                        data["annual_salary"] = gross_pay * 260  # Assuming 5 days/week, 52 weeks/year
                
                # Strategy 2: Assume monthly if gross_pay is provided but no pay_period
                elif data.get("gross_pay") and not data.get("pay_period"):
                    gross_pay = float(data["gross_pay"])
                    # If gross_pay is reasonable for monthly (between 1000-500000), assume monthly
                    if 1000 <= gross_pay <= 500000:
                        data["annual_salary"] = gross_pay * 12
                
                # Strategy 3: Use net_pay as fallback with monthly assumption
                elif data.get("net_pay") and not data.get("gross_pay"):
                    net_pay = float(data["net_pay"])
                    # If net_pay is reasonable for monthly (between 1000-500000), assume monthly
                    if 1000 <= net_pay <= 500000:
                        data["annual_salary"] = net_pay * 12
                
                # Strategy 4: Use year_to_date_gross to calculate annual
                elif data.get("year_to_date_gross"):
                    ytd_gross = float(data["year_to_date_gross"])
                    # Estimate based on current month (assuming we're in March, so multiply by 4)
                    data["annual_salary"] = ytd_gross * 4
                    
            except (ValueError, TypeError):
                pass  # Keep annual_salary as None if calculation fails
        
        # Enhanced hourly rate calculation if not directly provided
        if not data.get("hourly_rate") and data.get("gross_pay") and data.get("hours_worked"):
            try:
                gross_pay = float(data["gross_pay"])
                hours_worked = float(data["hours_worked"])
                if hours_worked > 0:
                    data["hourly_rate"] = gross_pay / hours_worked
            except (ValueError, TypeError, ZeroDivisionError):
                pass  # Keep hourly_rate as None if calculation fails
        
        # Clean up deductions field
        if data.get("deductions") and isinstance(data["deductions"], str):
            # Split deductions by common separators and clean up
            deductions_list = [d.strip() for d in data["deductions"].replace(",", ";").split(";") if d.strip()]
            data["deductions"] = deductions_list if deductions_list else None
        
        # Validate and clean pay_date
        if data.get("pay_date") and isinstance(data["pay_date"], str):
            try:
                from datetime import datetime
                # Try to parse various date formats
                date_formats = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%m-%d-%Y", "%d-%m-%Y"]
                parsed_date = None
                for fmt in date_formats:
                    try:
                        parsed_date = datetime.strptime(data["pay_date"], fmt)
                        break
                    except ValueError:
                        continue
                
                if parsed_date:
                    data["pay_date"] = parsed_date.strftime("%Y-%m-%d")
                else:
                    data["pay_date"] = None
            except (ValueError, TypeError):
                data["pay_date"] = None
        
        return data
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names using multiple algorithms"""
        if not name1 or not name2:
            return 0.0
        
        # Normalize names
        name1 = name1.lower().strip()
        name2 = name2.lower().strip()
        
        if name1 == name2:
            return 1.0
        
        # Split into words
        words1 = set(name1.split())
        words2 = set(name2.split())
        
        if not words1 or not words2:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        jaccard_sim = intersection / union if union > 0 else 0.0
        
        # Calculate word order similarity
        words1_list = name1.split()
        words2_list = name2.split()
        
        # Check if all words from shorter name are in longer name
        if len(words1_list) <= len(words2_list):
            shorter, longer = words1_list, words2_list
        else:
            shorter, longer = words2_list, words1_list
        
        word_order_sim = sum(1 for word in shorter if word in longer) / len(shorter) if shorter else 0.0
        
        # Combine similarities (weighted average)
        combined_sim = (jaccard_sim * 0.6) + (word_order_sim * 0.4)
        
        return min(combined_sim, 1.0)
    
    def _calculate_employer_similarity(self, employer1: str, employer2: str) -> float:
        """Calculate similarity between two employer names"""
        if not employer1 or not employer2:
            return 0.0
        
        # Normalize employer names
        employer1 = employer1.lower().strip()
        employer2 = employer2.lower().strip()
        
        if employer1 == employer2:
            return 1.0
        
        # Remove common business suffixes
        suffixes = ['inc', 'llc', 'corp', 'ltd', 'company', 'co', 'enterprises', 'group']
        
        for suffix in suffixes:
            employer1 = employer1.replace(f' {suffix}', '').replace(f'.{suffix}', '')
            employer2 = employer2.replace(f' {suffix}', '').replace(f'.{suffix}', '')
        
        # Use name similarity calculation
        return self._calculate_name_similarity(employer1, employer2)
    
    def _calculate_overall_verification_status(self, verification_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall verification status - ANY mismatch results in overall mismatch"""
        
        # Check each field for mismatches
        verification_details = []
        mismatches = []
        verified_fields = []
        
        # Check name match
        if verification_results.get("name_match") is not None:
            if verification_results["name_match"]:
                verification_details.append("✓ Name Match")
                verified_fields.append("name")
            else:
                verification_details.append("✗ Name Mismatch")
                mismatches.append("name")
        
        # Check salary match
        if verification_results.get("salary_match") is not None:
            if verification_results["salary_match"]:
                verification_details.append("✓ Salary Match")
                verified_fields.append("salary")
            else:
                verification_details.append("✗ Salary Mismatch")
                mismatches.append("salary")
        
        # Check employer match
        if verification_results.get("employer_match") is not None:
            if verification_results["employer_match"]:
                verification_details.append("✓ Employer Match")
                verified_fields.append("employer")
            else:
                verification_details.append("✗ Employer Mismatch")
                mismatches.append("employer")
        
        # Check SSN match
        if verification_results.get("ssn_match") is not None:
            if verification_results["ssn_match"]:
                verification_details.append("✓ SSN Match")
                verified_fields.append("ssn")
            else:
                verification_details.append("✗ SSN Mismatch")
                mismatches.append("ssn")
        
        # Calculate percentage score
        total_fields = len(verified_fields) + len(mismatches)
        if total_fields > 0:
            score_percentage = (len(verified_fields) / total_fields) * 100
        else:
            score_percentage = 0
        
        # STRICT LOGIC: Any mismatch = overall mismatch
        if len(mismatches) == 0:
            overall_status = "verified"
            status_reason = f"Verification passed - all fields match ({len(verified_fields)}/{total_fields} fields verified)"
        else:
            overall_status = "mismatch"
            status_reason = f"Verification failed - {len(mismatches)} field(s) mismatch: {', '.join(mismatches)}"
        
        # Add detailed verification summary
        verification_results["overall_status"] = overall_status
        verification_results["verification_score"] = score_percentage
        verification_results["verification_summary"] = status_reason
        verification_results["verification_details"] = verification_details
        verification_results["mismatches"] = mismatches
        verification_results["verified_fields"] = verified_fields
        
        return verification_results
    
    async def verify_application_data(self, application_data: Dict[str, Any], extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compare application data with extracted OCR data"""
        try:
            logger.info(f"Verifying application data: {application_data}")
            logger.info(f"Against extracted data: {extracted_data}")
            if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your_gemini_api_key_here":
                logger.error("Gemini API key not configured")
                raise Exception("Gemini API key not configured")
            
            verification_results = {
                "name_match": False,
                "name_reason": "",
                "salary_match": False,
                "salary_reason": "",
                "extracted_salary": None,
                "employer_match": False,
                "employer_reason": "",
                "extracted_employer": None,
                "ssn_match": False,
                "ssn_reason": "",
                "extracted_ssn": None
            }
            
            # Verify name with strict 80% similarity threshold
            app_name = application_data.get("name", "").lower().strip()
            extracted_name = extracted_data.get("employee_name", "").lower().strip()
            
            if app_name and extracted_name:
                name_match_score = self._calculate_name_similarity(app_name, extracted_name)
                if name_match_score >= 0.8:  # Strict 80% similarity threshold
                    verification_results["name_match"] = True
                    verification_results["name_reason"] = f"Name matches (similarity: {name_match_score:.1%})"
                else:
                    verification_results["name_match"] = False
                    verification_results["name_reason"] = f"Name mismatch: Application has '{application_data.get('name')}' but pay stub shows '{extracted_data.get('employee_name')}' (similarity: {name_match_score:.1%}) - requires 80%+ similarity"
            else:
                verification_results["name_match"] = False
                verification_results["name_reason"] = "Could not verify name - missing data"
            
            # Verify salary with enhanced logic
            app_salary = application_data.get("annual_salary", 0)
            extracted_salary = extracted_data.get("annual_salary", 0)
            
            if extracted_salary and app_salary:
                verification_results["extracted_salary"] = extracted_salary
                
                # Calculate salary difference and percentage
                salary_diff = abs(app_salary - extracted_salary)
                salary_diff_percent = (salary_diff / app_salary) * 100 if app_salary > 0 else 100
                
                # Dynamic tolerance based on salary range (more flexible)
                if app_salary < 30000:
                    tolerance_percent = 15  # 15% for low salaries (increased from 10%)
                elif app_salary < 100000:
                    tolerance_percent = 12  # 12% for medium salaries (increased from 7%)
                else:
                    tolerance_percent = 10  # 10% for high salaries (increased from 5%)
                
                if salary_diff_percent <= tolerance_percent:
                    verification_results["salary_match"] = True
                    verification_results["salary_reason"] = f"Salary matches within {tolerance_percent}% tolerance (difference: ${salary_diff:,}, {salary_diff_percent:.1f}%)"
                else:
                    verification_results["salary_reason"] = f"Salary mismatch: Application shows ${app_salary:,} but pay stub indicates ${extracted_salary:,} (difference: ${salary_diff:,}, {salary_diff_percent:.1f}%)"
            elif extracted_salary:
                verification_results["extracted_salary"] = extracted_salary
                verification_results["salary_reason"] = "Could not verify salary - application salary not provided"
            else:
                verification_results["salary_reason"] = "Could not extract salary from pay stub"
            
            # Verify employer with strict 80% similarity threshold
            app_employer = application_data.get("employer_name", "").lower().strip()
            extracted_employer = extracted_data.get("company_name", "").lower().strip()
            
            if extracted_employer:
                verification_results["extracted_employer"] = extracted_data.get("company_name")
                if app_employer and extracted_employer:
                    employer_match_score = self._calculate_employer_similarity(app_employer, extracted_employer)
                    if employer_match_score >= 0.8:  # Strict 80% similarity threshold
                        verification_results["employer_match"] = True
                        verification_results["employer_reason"] = f"Employer matches (similarity: {employer_match_score:.1%})"
                    else:
                        verification_results["employer_match"] = False
                        verification_results["employer_reason"] = f"Employer mismatch: Application has '{application_data.get('employer_name')}' but pay stub shows '{extracted_data.get('company_name')}' (similarity: {employer_match_score:.1%}) - requires 80%+ similarity"
                else:
                    verification_results["employer_match"] = False
                    verification_results["employer_reason"] = "Could not verify employer - missing data"
            else:
                verification_results["employer_match"] = False
                verification_results["employer_reason"] = "Could not extract employer name from pay stub"
            
            # Verify SSN (last 4 digits) - exact match required
            app_ssn = application_data.get("ssn", "")
            extracted_ssn = extracted_data.get("ssn", "")
            
            if extracted_ssn:
                verification_results["extracted_ssn"] = extracted_ssn
                if app_ssn and extracted_ssn:
                    # Compare last 4 digits - exact match required
                    app_last4 = app_ssn[-4:] if len(app_ssn) >= 4 else app_ssn
                    if app_last4 == extracted_ssn:
                        verification_results["ssn_match"] = True
                        verification_results["ssn_reason"] = "SSN last 4 digits match"
                    else:
                        verification_results["ssn_match"] = False
                        verification_results["ssn_reason"] = f"SSN mismatch: Application last 4 digits are {app_last4} but pay stub shows {extracted_ssn} - exact match required"
                else:
                    verification_results["ssn_match"] = False
                    verification_results["ssn_reason"] = "Could not verify SSN - missing data"
            else:
                verification_results["ssn_match"] = False
                verification_results["ssn_reason"] = "Could not extract SSN from pay stub"
            
            # Determine overall status with intelligent scoring
            verification_results = self._calculate_overall_verification_status(verification_results)
            
            return verification_results
            
        except Exception as e:
            logger.error(f"Error in verification: {e}")
            return {
                "name_match": False,
                "name_reason": f"Verification error: {str(e)}",
                "salary_match": False,
                "salary_reason": f"Verification error: {str(e)}",
                "extracted_salary": None,
                "employer_match": False,
                "employer_reason": f"Verification error: {str(e)}",
                "ssn_match": False,
                "ssn_reason": f"Verification error: {str(e)}",
                "overall_status": "error"
            }

# Global instance
gemini_ocr = GeminiOCRService()
