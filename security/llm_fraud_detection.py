"""
LLM-Based Fraud Detection for Rural Banking
Advanced fraud detection using Large Language Models
"""

import json
import time
import requests
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import hashlib

class LLMProvider(Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    HUGGINGFACE = "huggingface"
    LOCAL = "local"
    OLLAMA = "ollama"

@dataclass
class LLMFraudResult:
    """LLM fraud detection result"""
    is_fraud: bool
    confidence: float
    risk_level: str
    reasoning: str
    risk_factors: List[str]
    recommended_action: str
    processing_time: float

class LLMFraudDetector:
    """LLM-based fraud detection system"""
    
    def __init__(self, provider: LLMProvider = LLMProvider.LOCAL):
        self.provider = provider
        self.model_config = self._get_model_config()
        self.prompt_template = self._get_fraud_prompt_template()
        
    def _get_model_config(self) -> Dict[str, Any]:
        """Get model configuration based on provider"""
        configs = {
            LLMProvider.LOCAL: {
                "model": "local_fraud_model",
                "endpoint": "http://localhost:11434/api/generate",
                "max_tokens": 500,
                "temperature": 0.1
            },
            LLMProvider.OLLAMA: {
                "model": "llama2:7b",
                "endpoint": "http://localhost:11434/api/generate",
                "max_tokens": 500,
                "temperature": 0.1
            },
            LLMProvider.HUGGINGFACE: {
                "model": "microsoft/DialoGPT-medium",
                "endpoint": "https://api-inference.huggingface.co/models/",
                "max_tokens": 500,
                "temperature": 0.1
            }
        }
        return configs.get(self.provider, configs[LLMProvider.LOCAL])
    
    def _get_fraud_prompt_template(self) -> str:
        """Get fraud detection prompt template"""
        return """
You are an expert fraud detection system for rural banking. Analyze the following transaction data and determine if it's fraudulent.

TRANSACTION DATA:
- User ID: {user_id}
- Amount: ₹{amount}
- Time: {transaction_time}
- Device: {device_id}
- Location Pattern: {location_pattern}
- User History: {user_history}
- Behavioral Patterns: {behavioral_patterns}

CONTEXT:
- This is a rural banking system serving low-income users
- Typical transaction amounts: ₹100 - ₹10,000
- Unusual patterns: Very high amounts, rapid transactions, unusual times
- User profile: {user_profile}

ANALYSIS REQUIRED:
1. Is this transaction fraudulent? (YES/NO)
2. Confidence level (0.0 to 1.0)
3. Risk level (LOW/MEDIUM/HIGH/CRITICAL)
4. Specific risk factors identified
5. Recommended action

Respond in JSON format:
{{
    "is_fraud": boolean,
    "confidence": float,
    "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
    "reasoning": "detailed explanation",
    "risk_factors": ["factor1", "factor2"],
    "recommended_action": "action to take"
}}

Focus on patterns typical in rural banking fraud:
- Unusually high amounts for rural users
- Rapid succession of transactions
- Transactions at unusual hours
- Sudden changes in spending patterns
- Device/location inconsistencies
"""

    def analyze_transaction_with_llm(self, user_id: str, transaction_data: Dict[str, Any], 
                                   user_profile: Dict[str, Any]) -> LLMFraudResult:
        """Analyze transaction using LLM"""
        start_time = time.time()
        
        try:
            # Prepare context data
            context = self._prepare_transaction_context(user_id, transaction_data, user_profile)
            
            # Generate prompt
            prompt = self.prompt_template.format(**context)
            
            # Call LLM
            llm_response = self._call_llm(prompt)
            
            # Parse response
            result = self._parse_llm_response(llm_response)
            
            processing_time = time.time() - start_time
            
            return LLMFraudResult(
                is_fraud=result.get('is_fraud', False),
                confidence=result.get('confidence', 0.5),
                risk_level=result.get('risk_level', 'MEDIUM'),
                reasoning=result.get('reasoning', 'LLM analysis completed'),
                risk_factors=result.get('risk_factors', []),
                recommended_action=result.get('recommended_action', 'Monitor transaction'),
                processing_time=processing_time
            )
            
        except Exception as e:
            logging.error(f"LLM fraud detection failed: {e}")
            # Fallback to rule-based detection
            return self._fallback_detection(transaction_data, user_profile, time.time() - start_time)
    
    def _prepare_transaction_context(self, user_id: str, transaction_data: Dict[str, Any], 
                                   user_profile: Dict[str, Any]) -> Dict[str, str]:
        """Prepare context for LLM prompt"""
        amount = transaction_data.get('amount', 0)
        timestamp = transaction_data.get('timestamp', time.time())
        device_id = transaction_data.get('device_id', 'unknown')
        
        # Generate behavioral patterns summary
        behavioral_patterns = self._analyze_behavioral_patterns(user_profile)
        
        # Generate user history summary
        user_history = self._summarize_user_history(user_profile)
        
        return {
            'user_id': user_id,
            'amount': f"{amount:,.2f}",
            'transaction_time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp)),
            'device_id': device_id,
            'location_pattern': user_profile.get('location_pattern', 'consistent'),
            'user_history': user_history,
            'behavioral_patterns': behavioral_patterns,
            'user_profile': json.dumps(user_profile, indent=2)
        }
    
    def _analyze_behavioral_patterns(self, user_profile: Dict[str, Any]) -> str:
        """Analyze user behavioral patterns"""
        patterns = []
        
        avg_amount = user_profile.get('avg_amount', 0)
        if avg_amount > 0:
            patterns.append(f"Average transaction: ₹{avg_amount:,.2f}")
        
        transaction_count = user_profile.get('transaction_count', 0)
        patterns.append(f"Total transactions: {transaction_count}")
        
        last_transaction = user_profile.get('last_transaction_time', 0)
        if last_transaction > 0:
            hours_since = (time.time() - last_transaction) / 3600
            patterns.append(f"Last transaction: {hours_since:.1f} hours ago")
        
        return "; ".join(patterns) if patterns else "Limited history available"
    
    def _summarize_user_history(self, user_profile: Dict[str, Any]) -> str:
        """Summarize user transaction history"""
        history_items = []
        
        if user_profile.get('is_new_user', True):
            history_items.append("New user with limited history")
        else:
            history_items.append("Established user")
        
        risk_score = user_profile.get('risk_score', 0.5)
        history_items.append(f"Historical risk score: {risk_score:.2f}")
        
        return "; ".join(history_items)
    
    def _call_llm(self, prompt: str) -> str:
        """Call the configured LLM"""
        if self.provider == LLMProvider.OLLAMA:
            return self._call_ollama(prompt)
        elif self.provider == LLMProvider.LOCAL:
            return self._call_local_model(prompt)
        else:
            # Fallback to simulated response
            return self._simulate_llm_response(prompt)
    
    def _call_ollama(self, prompt: str) -> str:
        """Call Ollama local LLM"""
        try:
            payload = {
                "model": self.model_config["model"],
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.model_config["temperature"],
                    "num_predict": self.model_config["max_tokens"]
                }
            }
            
            response = requests.post(
                self.model_config["endpoint"],
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get("response", "")
            else:
                raise Exception(f"Ollama API error: {response.status_code}")
                
        except Exception as e:
            logging.error(f"Ollama call failed: {e}")
            raise
    
    def _call_local_model(self, prompt: str) -> str:
        """Call local model (placeholder for custom implementation)"""
        # This would integrate with your local model
        # For now, return a simulated response
        return self._simulate_llm_response(prompt)
    
    def _simulate_llm_response(self, prompt: str) -> str:
        """Simulate LLM response for testing"""
        # Extract amount from prompt for basic rule-based simulation
        amount_str = prompt.split("Amount: ₹")[1].split("\n")[0] if "Amount: ₹" in prompt else "0"
        try:
            amount = float(amount_str.replace(",", ""))
        except:
            amount = 0
        
        # Simple rule-based simulation
        if amount > 100000:
            return json.dumps({
                "is_fraud": True,
                "confidence": 0.85,
                "risk_level": "HIGH",
                "reasoning": "Transaction amount significantly exceeds typical rural banking patterns. Amount of ₹{:,.2f} is unusually high for rural users.".format(amount),
                "risk_factors": ["High amount transaction", "Exceeds rural banking norms"],
                "recommended_action": "Block transaction and require manual verification"
            })
        elif amount > 50000:
            return json.dumps({
                "is_fraud": False,
                "confidence": 0.65,
                "risk_level": "MEDIUM",
                "reasoning": "Transaction amount is elevated but within acceptable range for rural banking with additional verification.",
                "risk_factors": ["Elevated amount"],
                "recommended_action": "Require additional authentication"
            })
        else:
            return json.dumps({
                "is_fraud": False,
                "confidence": 0.9,
                "risk_level": "LOW",
                "reasoning": "Transaction amount and patterns are consistent with normal rural banking activity.",
                "risk_factors": [],
                "recommended_action": "Allow transaction"
            })
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM JSON response"""
        try:
            # Try to extract JSON from response
            if "{" in response and "}" in response:
                start = response.find("{")
                end = response.rfind("}") + 1
                json_str = response[start:end]
                return json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
        except Exception as e:
            logging.error(f"Failed to parse LLM response: {e}")
            # Return default response
            return {
                "is_fraud": False,
                "confidence": 0.5,
                "risk_level": "MEDIUM",
                "reasoning": "Unable to parse LLM response",
                "risk_factors": ["LLM parsing error"],
                "recommended_action": "Use fallback detection"
            }
    
    def _fallback_detection(self, transaction_data: Dict[str, Any], 
                          user_profile: Dict[str, Any], processing_time: float) -> LLMFraudResult:
        """Fallback rule-based detection when LLM fails"""
        amount = transaction_data.get('amount', 0)
        
        if amount > 100000:
            return LLMFraudResult(
                is_fraud=True,
                confidence=0.8,
                risk_level="HIGH",
                reasoning="Fallback rule: High amount transaction",
                risk_factors=["High amount"],
                recommended_action="Block transaction",
                processing_time=processing_time
            )
        else:
            return LLMFraudResult(
                is_fraud=False,
                confidence=0.7,
                risk_level="LOW",
                reasoning="Fallback rule: Normal transaction",
                risk_factors=[],
                recommended_action="Allow transaction",
                processing_time=processing_time
            )

# Global LLM fraud detector instance
llm_fraud_detector = LLMFraudDetector(LLMProvider.LOCAL)
