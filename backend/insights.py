
import os
from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition

# Load environment variables
load_dotenv()

class InsightsService:
    def __init__(self, db):
        self.db = db
        self.insights_collection = db["insights"]
        
        # Initialize Qdrant client directly
        self.qdrant_client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY")
        )
        self.qdrant_collection = "mongodb_to_qdrant"  # Your Qdrant collection name
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
    def _search_qdrant(self, medicine_name: str, label: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Search Qdrant directly for documents matching medicine_name and optional label"""
        try:
            # Create filter conditions
            must_conditions = [
                FieldCondition(key="medicine_name", match={"value": medicine_name})
            ]
            
            if label:
                must_conditions.append(
                    FieldCondition(key="label", match={"value": label})
                )
            
            # Use scroll instead of search for metadata filtering
            scroll_result = self.qdrant_client.scroll(
                collection_name=self.qdrant_collection,
                scroll_filter=Filter(must=must_conditions),
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
            
            # Format results
            return [{
                'payload': record.payload,
                'id': record.id
            } for record in scroll_result[0]]
            
        except Exception as e:
            print(f"Error searching Qdrant: {str(e)}")
            return []

    def generate_insights(self, medicine_name: str, label: Optional[str] = None):
        """Generate insights using data directly from Qdrant"""
        try:
            print(f"Starting insight generation for {medicine_name} - {label or 'all labels'}")
            
            # Get documents from Qdrant
            qdrant_results = self._search_qdrant(medicine_name, label)
            
            if not qdrant_results:
                print(f"No documents found for {medicine_name} with label {label}")
                return None
            
            # Prepare context data
            context = {
                "medicine_name": medicine_name,
                "label": label,
                "document_count": len(qdrant_results),
                "labels": {},
                "sample_documents": []
            }
            
            # Process labels and reasons
            label_data = {}
            for result in qdrant_results:
                payload = result['payload']
                current_label = payload.get('label')
                reason = payload.get('label_reason', '')
                
                if current_label not in label_data:
                    label_data[current_label] = {
                        "count": 0,
                        "reasons": set()
                    }
                label_data[current_label]["count"] += 1
                if reason:
                    label_data[current_label]["reasons"].add(reason)
            
            # Convert sets to lists
            for lbl in label_data:
                label_data[lbl]["reasons"] = list(label_data[lbl]["reasons"])
            
            context["labels"] = label_data
            
            # Add sample documents (first 3)
            for result in qdrant_results[:3]:
                payload = result['payload']
                context["sample_documents"].append({
                    "text": payload.get('text', '')[:200] + ("..." if len(payload.get('text', '')) > 200 else ""),
                    "labels": [payload.get('label', '')],
                    "label_reasons": {payload.get('label', ''): payload.get('label_reason', '')}
                })
            
            # Generate prompt and get insights
            prompt = self._create_insight_prompt(medicine_name, label, label_data, qdrant_results)
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a pharmaceutical business analyst."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            insights = response.choices[0].message.content
            
            # Store insights in MongoDB
            insight_doc = {
                "medicine_name": medicine_name,
                "label": label,
                "insights": insights,
                "context": context,
                "generated_at": datetime.now(),
                "document_count": len(qdrant_results)
            }
            
            self.insights_collection.insert_one(insight_doc)
            print(f"Successfully generated insights for {medicine_name}")
            
            return insight_doc
            
        except Exception as e:
            print(f"Error generating insights: {str(e)}")
            return None

    # ... (keep other existing methods)


    # def _create_insight_prompt(self, medicine_name: str, label: Optional[str], label_data: Dict, documents: List[Dict]) -> str:
    #         """Create the prompt for insight generation"""
    #         prompt = f"""
    # **Objective:**
    # Generate comprehensive business insights for the medicine {medicine_name} based on collected transcripts.
    # {f"Focusing specifically on the label: {label}" if label else "Analyzing all available labels."}

    # **Context:**
    # - Total documents analyzed: {len(documents)}
    # - Labels found: {len(label_data)}
    # {f"- Specific label being analyzed: {label}" if label else ""}

    # **Label Data:**
    # """
    #         for lbl, data in label_data.items():
    #             prompt += f"- {lbl} (appears in {data['count']} documents):\n"
    #             for reason in data.get("reasons", []):
    #                 prompt += f"  - Reason: {reason}\n"
            
    #         prompt += """
    # **Instructions:**
    # 1. Analyze the label data and reasons to identify patterns and trends.
    # 2. Provide actionable business insights for product managers and marketing teams.
    # 3. Focus on the labels and how can we improve our market position in positive way and also give suggestions if there are any negative labels.
    # 4. Structure your response with clear sections in paragraph format**.
    # 5. Keep the language professional but accessible.
    # 6. Include specific recommendations where possible.

    # **Output Format:**
    # Provide a detailed analysis in the following structure:
    # -[Important**]To the main topic and showing insights which are business useful and relevant to the business perspective.
    # -The summary should have detail and conscise information where the business is doing well and where they need to improve and work on the business for the same 
    # - The Summary should be detailed and extended and should be in paragraph format and not in bullet points. 
    # - The Summary should be in the detailed with no useless information and should be in the business perspective and should be in the business language and should be in the business format


    # - **Executive Summary** (2-3 sentences)
    # - **Key Findings** (bullet points)
    # - **Opportunities** (specific actionable items)
    # - **Recommendations** (concrete next steps)
    # in paragraph format.

    # **Example:**
    # The analysis of [Medicine] indicates strong acceptance among doctors, with many consistently praising the product's efficacy. However, pricing has emerged as a significant concern when compared to competitors. Notably, 65% of transcripts highlight competitive pricing as a key barrier to adoption. To address this, there are opportunities to develop targeted discount programs specifically for high-prescribing doctors, along with the creation of marketing materials that emphasize the medicine's superior efficacy. In light of these insights, it is recommended to conduct a detailed pricing study within the next quarter and to organize medical representative (MR) training sessions focused on effectively addressing pricing objections.

    # **Now generate insights for {medicine_name}:**
    # **Required Output Format:**

    # # {medicine_name}

    # **Feedback**
    # [Summary of positive and negative feedback, 2-3 concise bullet points]

    # ---

    # ## Competition
    # [Main competitors and market position, 1-2 sentences]

    # ---

    # ## Pricing
    # [Pricing analysis and suggestions, 1-2 sentences]

    # ---

    # ## MR Suggestions
    # [2-3 actionable suggestions for medical representatives]

    # ---

    # ## Additional Insights
    # [Any other relevant insights]

    # Keep each section concise and focused. Use bullet points where appropriate.
    # """
    #         prompt += f"\n\n**Context Data:**\n- Total documents: {len(documents)}\n"
    #         for lbl, data in label_data.items():
    #             prompt += f"- {lbl} ({data['count']} documents):\n"
    #             for reason in data.get("reasons", []):
    #                 prompt += f"  - {reason}\n"
            
    #         return prompt


    def _create_insight_prompt(self, medicine_name: str, label: Optional[str], label_data: Dict, documents: List[Dict]) -> str:
            """Create the prompt for insight generation"""
            prompt = f"""
    **Objective:**
    Generate comprehensive business insights for the medicine {medicine_name} based on collected transcripts.
    {f"Focusing specifically on the label: {label}" if label else "Analyzing all available labels."}

    **Context:**
    - Total documents analyzed: {len(documents)}
    - Labels found: {len(label_data)}
    {f"- Specific label being analyzed: {label}" if label else ""}

    **Label Data:**
    """
            for lbl, data in label_data.items():
                prompt += f"- {lbl} (appears in {data['count']} documents):\n"
                for reason in data.get("reasons", []):
                    prompt += f"  - Reason: {reason}\n"
            
            prompt += """
#     You are an expert analyst in pharmaceutical business conversations and strategy.

#     Your task is to analyze the following texts carefully and identify the **top 5 most important and business-relevant themes** for the product: **{medicine_name}**.

#     Each theme must follow these rules:
#     - Theme names must be **short and clear**, with a **maximum of 4 words**.
#     - Each theme should highlight a distinct area of insight useful for brand growth, doctor engagement, or field execution.

#     For **each theme**, provide:
#     1. **Insight**: A list of **2 to 3 concise bullet points**, each not more than one sentence, summarizing the key observations from the text. These insights should give meaningful understanding to pharma business heads to help in strategic decisions and understand the current ground reality, pain points, market conditions, or opportunities.
#     2. **Action**: A list of **2 to 3 actionable recommendations**, each not more than one sentence, suggesting practical next steps. These actions should:
#     - Help grow sales,
#     - Improve field force efforts,
#     - Strengthen engagement with healthcare professionals (HCPs),
#     - Or improve the brand's positioning.

Important Guidelines:
#     - Base all insights/actions **strictly on the content** of the texts. Do **not invent** or generalize.
#     - Avoid redundant or vague points.
#     - Focus on **clarity**, **impact**, and **practical value** for decision-makers and field teams.
#     - Make sure actions are **feasible** and **business-impactful** (e.g. messaging improvement, training needs, HCP education, product differentiation, etc.)


    **Example:**
    The analysis of [Medicine] indicates strong acceptance among doctors, with many consistently praising the product's efficacy. However, pricing has emerged as a significant concern when compared to competitors. Notably, 65% of transcripts highlight competitive pricing as a key barrier to adoption. To address this, there are opportunities to develop targeted discount programs specifically for high-prescribing doctors, along with the creation of marketing materials that emphasize the medicine's superior efficacy. In light of these insights, it is recommended to conduct a detailed pricing study within the next quarter and to organize medical representative (MR) training sessions focused on effectively addressing pricing objections.

    **Now generate insights for {medicine_name}:**
    **Required Output Format:**

    # {medicine_name}

    **Feedback**
    [Summary of positive and negative feedback, 2-3 concise bullet points]

    ---

    ## Competition
    [Main competitors and market position, 1-2 sentences]

    ---

    ## Pricing
    [Pricing analysis and suggestions, 1-2 sentences]

    ---

    ## MR Suggestions
    [2-3 actionable suggestions for medical representatives]

    ---

    ## Additional Insights
    [Any other relevant insights]

    Keep each section concise and focused. Use bullet points where appropriate.
    """
            prompt += f"\n\n**Context Data:**\n- Total documents: {len(documents)}\n"
            for lbl, data in label_data.items():
                prompt += f"- {lbl} ({data['count']} documents):\n"
                for reason in data.get("reasons", []):
                    prompt += f"  - {reason}\n"
            
            return prompt


# def summarize_texts(texts: List[str], product: str) -> str:
#     prompt = f"""
#     You are an expert analyst in pharmaceutical business conversations and strategy.

#     Your task is to analyze the following texts carefully and identify the **top 5 most important and business-relevant themes** for the product: **{product}**.

#     Each theme must follow these rules:
#     - Theme names must be **short and clear**, with a **maximum of 4 words**.
#     - Each theme should highlight a distinct area of insight useful for brand growth, doctor engagement, or field execution.

#     For **each theme**, provide:
#     1. **Insight**: A list of **2 to 3 concise bullet points**, each not more than one sentence, summarizing the key observations from the text. These insights should give meaningful understanding to pharma business heads to help in strategic decisions and understand the current ground reality, pain points, market conditions, or opportunities.
#     2. **Action**: A list of **2 to 3 actionable recommendations**, each not more than one sentence, suggesting practical next steps. These actions should:
#     - Help grow sales,
#     - Improve field force efforts,
#     - Strengthen engagement with healthcare professionals (HCPs),
#     - Or improve the brand's positioning.

#     Important Guidelines:
#     - Base all insights/actions **strictly on the content** of the texts. Do **not invent** or generalize.
#     - Avoid redundant or vague points.
#     - Focus on **clarity**, **impact**, and **practical value** for decision-makers and field teams.
#     - Make sure actions are **feasible** and **business-impactful** (e.g. messaging improvement, training needs, HCP education, product differentiation, etc.)

#     **IMPORTANT:** Return your answer **only** as a fenced code block labeled json, exactly like this:
   
# json
#     [
#     {{
#         "theme": "Theme Name",
#         "insight": [
#         "Insight point 1",
#         "Insight point 2",
#         "Insight point 3"
#         ],
#         "action": [
#         "Action point 1",
#         "Action point 2",
#         "Action point 3"
#         ]
#     }}
#     ]
   
#     """ + "\n".join(texts)

    # ... (rest of the methods remain the same)
    def get_insights_history(self, medicine_name: Optional[str] = None, label: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Get historical insights with optional filters"""
        query = {}
        if medicine_name:
            query["medicine_name"] = medicine_name
        if label:
            query["label"] = label
        
        return list(self.insights_collection.find(query).sort("generated_at", -1).limit(limit))
    

    def _generate_label_summary(self, medicine_name: str, label_data: Dict) -> str:
        """Generate a summary of all labels for a medicine"""
        try:
            if not label_data:
                return f"No labels found for {medicine_name}"
            
            # Prepare prompt for OpenAI
            prompt = f"""
Generate a comprehensive business summary for {medicine_name} based on the following label data:

**Labels and Reasons:**
"""
            for label, data in label_data.items():
                prompt += f"- {label} (appears in {data['count']} documents):\n"
                for reason in data.get("reasons", []):
                    prompt += f"  - {reason}\n"
            
            prompt += """
**Instructions:**
1. Analyze the label data to identify key themes and patterns.
2. Provide sentence summary of the overall business insights.
3. Focus on market trends, competitive positioning, and opportunities.
4. Keep the language professional and concise.

**Output Format:**
Return only the summary text, no additional formatting or labels.
"""
            # Call OpenAI API (updated for v1.0+)
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a pharmaceutical business analyst."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error generating label summary: {str(e)}")
            return f"Summary generation failed: {str(e)}"

    def get_medicine_labels_with_reasons(self, medicine_name: str) -> Dict[str, Any]:
        """Get labels and reasons directly from Qdrant"""
        try:
            results = self._search_qdrant(medicine_name)
            
            if not results:
                return {
                    "medicine_name": medicine_name,
                    "labels": [],
                    "summary": "No documents found"
                }
            
            label_data = {}
            for result in results:
                payload = result['payload']
                label = payload.get('label')
                reason = payload.get('label_reason', '')
                text = payload.get('text', '')
                
                if label not in label_data:
                    label_data[label] = {
                        "count": 0,
                        "reasons": set(),
                        "sample_texts": set()
                    }
                label_data[label]["count"] += 1
                if reason:
                    label_data[label]["reasons"].add(reason)
                if text:
                    sample = text[:100] + ("..." if len(text) > 100 else "")
                    label_data[label]["sample_texts"].add(sample)
            
            # Convert sets to lists
            for label in label_data:
                label_data[label]["reasons"] = list(label_data[label]["reasons"])
                label_data[label]["sample_texts"] = list(label_data[label]["sample_texts"])
            
            # Generate summary (use your existing _generate_label_summary method)
            summary = self._generate_label_summary(medicine_name, label_data)
            
            return {
                "medicine_name": medicine_name,
                "labels": label_data,
                "summary": summary,
                "document_count": len(results)
            }
            
        except Exception as e:
            print(f"Error getting labels: {str(e)}")
            return {
                "medicine_name": medicine_name,
                "error": str(e)
            }

# Initialize service
def init_insights_service(db):
    return InsightsService(db)