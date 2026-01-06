"""
Cover Letter Body Generator (Async Version)

Generates natural, ATS-optimized cover letter bodies that:
- Match the job offer language
- Integrate seamlessly with header/signature
- Avoid AI detection patterns
- Fit on one page when combined with other elements
"""

import os
from typing import Dict, Any, Optional
from openai import AsyncOpenAI
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils.config_loader import get_config


async def generate_cover_letter(
    job_data: Dict[str, Any],
    enhanced_experiences: list,
    profile_text: str,
    skills: list,
    client: AsyncOpenAI,
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a cover letter body based on job offer and enhanced resume (ASYNC).

    Args:
        job_data: Structured job data from structuring step
        enhanced_experiences: Enhanced bullet results from enhancement
        profile_text: Profile summary text
        skills: List of technical skills
        client: AsyncOpenAI client
        model: OpenAI model to use (default: from config)

    Returns:
        dict: Result containing:
            - success (bool): Whether generation succeeded
            - cover_letter_body (str): Generated cover letter body text
            - language (str): Detected language (fr/en)
            - metadata (dict): Generation metadata (word_count, paragraph_count, etc.)
            - usage (dict): Token usage and cost info
            - error (str): Error message if failed
    """
    # Load model from config if not provided
    if model is None:
        model = get_config('cover_letter.model', 'gpt-4o-mini')

    try:
        # Detect language from job data
        language = job_data.get("metadata", {}).get("language", "fr").lower()

        # Build project highlights from enhanced experiences
        project_highlights = []
        for exp in enhanced_experiences[:3]:  # Top 3 projects
            project_name = exp.get("project_name", "")
            bullets = exp.get("bullets", [])
            if bullets:
                # Take the top 2 bullets per project
                top_bullets = [b.get("text", "") for b in bullets[:2]]
                project_highlights.append({
                    "name": project_name,
                    "achievements": top_bullets
                })

        # Create the prompt
        prompt = _build_prompt(
            job_data=job_data,
            profile_text=profile_text,
            project_highlights=project_highlights,
            skills=skills,
            language=language
        )

        # Load generation parameters from config
        temperature = get_config('cover_letter.temperature', 0.7)
        max_tokens = get_config('cover_letter.max_tokens', 800)

        print(f"\n  Generating cover letter (model: {model}, lang: {language})...")

        # Call OpenAI API (ASYNC)
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": _get_system_prompt(language)
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )

        cover_letter_body = response.choices[0].message.content.strip()

        # Calculate usage and cost
        usage = {
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }

        # Load pricing from config
        input_price = get_config(f'openai.pricing.{model}.input_per_million', 0.15)
        output_price = get_config(f'openai.pricing.{model}.output_per_million', 0.60)
        cost = (usage['input_tokens'] * input_price / 1_000_000 +
                usage['output_tokens'] * output_price / 1_000_000)

        # Calculate metadata
        paragraphs = [p.strip() for p in cover_letter_body.split('\n\n') if p.strip()]
        word_count = len(cover_letter_body.split())

        metadata = {
            "language": language,
            "word_count": word_count,
            "paragraph_count": len(paragraphs),
            "estimated_lines": word_count // 12,
            "model": model
        }

        print(f"  [OK] Cover letter generated ({word_count} words, {len(paragraphs)} paragraphs)")

        return {
            "success": True,
            "cover_letter_body": cover_letter_body,
            "language": language,
            "metadata": metadata,
            "usage": usage,
            "cost": cost,
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "cover_letter_body": None
        }


def _get_system_prompt(language: str) -> str:
    """Get the system prompt based on language."""
    if language == "en":
        return """You are an expert career coach and professional writer specializing in cover letters.

Your task is to write ONLY the body paragraphs of a cover letter (NOT the header, greeting, or closing).

Requirements:
- Write 3-4 paragraphs maximum
- Keep it concise and impactful (300-400 words total)
- Use natural, authentic language that sounds human-written
- Avoid clichés like "I am writing to express my interest"
- Be specific with examples and achievements
- Match the company's tone and values
- Optimize for ATS with relevant keywords naturally integrated
- Focus on value proposition: what YOU bring to THEM
- End with a forward-looking statement (no closing formula)

DO NOT include:
- Header with contact information
- Opening greeting (Dear...)
- Closing formula (Sincerely, Best regards, etc.)
- Signature

Start directly with the first body paragraph."""
    else:  # French
        return """Vous êtes un expert en orientation professionnelle et rédacteur professionnel spécialisé dans les lettres de motivation.

Votre tâche est d'écrire UNIQUEMENT le corps de la lettre (PAS l'en-tête, la formule d'appel ou la formule de politesse finale).

Exigences :
- Écrire 3-4 paragraphes maximum
- Rester concis et percutant (300-400 mots au total)
- Utiliser un langage naturel et authentique qui semble rédigé par un humain
- Éviter les clichés comme "Je me permets de vous adresser ma candidature"
- Être spécifique avec des exemples et réalisations concrètes
- S'aligner sur le ton et les valeurs de l'entreprise
- Optimiser pour les ATS avec une intégration naturelle des mots-clés
- Se concentrer sur la proposition de valeur : ce que VOUS apportez à L'ENTREPRISE
- Terminer par une phrase tournée vers l'avenir (pas de formule de politesse)

NE PAS inclure :
- En-tête avec coordonnées
- Formule d'appel (Madame, Monsieur,...)
- Formule de politesse finale (Cordialement, etc.)
- Signature

Commencer directement par le premier paragraphe du corps."""


def _build_prompt(
    job_data: Dict[str, Any],
    profile_text: str,
    project_highlights: list,
    skills: list,
    language: str
) -> str:
    """Build the user prompt with job and resume context."""

    # Extract job details
    job_title = job_data.get('job_title', '').strip()
    company_name = job_data.get('company_name', '').strip()
    city = job_data.get('location', {}).get('city', '').strip()

    if language == "en":
        prompt = "Write the body paragraphs for a cover letter"

        # Build job details section
        job_details_parts = []
        if job_title:
            job_details_parts.append(f"- Position: {job_title}")
        if company_name:
            job_details_parts.append(f"- Company: {company_name}")
        if city:
            job_details_parts.append(f"- Location: {city}")

        if job_details_parts:
            prompt += " for this position:\n\nJOB DETAILS:\n" + "\n".join(job_details_parts)
        else:
            prompt += ":\n\nJOB OPPORTUNITY"

        # Add requirements
        prompt += "\n\nKEY REQUIREMENTS:\n"
        must_have = job_data.get('technical_priorities', {}).get('must_have', [])[:5]
        preferred = job_data.get('technical_priorities', {}).get('preferred', [])[:5]
        soft_skills_list = job_data.get('soft_skills', [])[:4]

        if must_have:
            prompt += f"- Must-have skills: {', '.join(must_have)}\n"
        if preferred:
            prompt += f"- Preferred skills: {', '.join(preferred)}\n"
        if soft_skills_list:
            prompt += f"- Soft skills: {', '.join(soft_skills_list)}\n"

        keywords = job_data.get('keywords', [])[:10]
        if keywords:
            prompt += f"\nCOMPANY VALUES/KEYWORDS:\n{', '.join(keywords)}\n"

        prompt += f"\nMY PROFILE:\n{profile_text}\n"
        prompt += "\nMY KEY PROJECTS & ACHIEVEMENTS:\n"

        for i, proj in enumerate(project_highlights, 1):
            prompt += f"\n{i}. {proj['name']}:\n"
            for achievement in proj['achievements']:
                prompt += f"   - {achievement}\n"

        prompt += f"\nMY TECHNICAL SKILLS: {', '.join(skills[:12])}\n"

        # Final instruction
        if job_title and company_name:
            prompt += f"\nWrite a compelling cover letter body that demonstrates why I'm the perfect fit for the {job_title} role at {company_name}."
        elif job_title:
            prompt += f"\nWrite a compelling cover letter body that demonstrates why I'm the perfect fit for the {job_title} role."
        elif company_name:
            prompt += f"\nWrite a compelling cover letter body that demonstrates why I'm the perfect fit for this role at {company_name}."
        else:
            prompt += "\nWrite a compelling cover letter body that demonstrates why I'm the perfect fit for this opportunity."

    else:  # French
        prompt = "Rédigez le corps d'une lettre de motivation"

        # Build job details section
        job_details_parts = []
        if job_title:
            job_details_parts.append(f"- Poste : {job_title}")
        if company_name:
            job_details_parts.append(f"- Entreprise : {company_name}")
        if city:
            job_details_parts.append(f"- Localisation : {city}")

        if job_details_parts:
            prompt += " pour ce poste :\n\nDÉTAILS DU POSTE :\n" + "\n".join(job_details_parts)
        else:
            prompt += ":\n\nOPPORTUNITÉ PROFESSIONNELLE"

        # Add requirements
        prompt += "\n\nCOMPÉTENCES REQUISES :\n"
        must_have = job_data.get('technical_priorities', {}).get('must_have', [])[:5]
        preferred = job_data.get('technical_priorities', {}).get('preferred', [])[:5]
        soft_skills_list = job_data.get('soft_skills', [])[:4]

        if must_have:
            prompt += f"- Compétences essentielles : {', '.join(must_have)}\n"
        if preferred:
            prompt += f"- Compétences souhaitées : {', '.join(preferred)}\n"
        if soft_skills_list:
            prompt += f"- Soft skills : {', '.join(soft_skills_list)}\n"

        keywords = job_data.get('keywords', [])[:10]
        if keywords:
            prompt += f"\nVALEURS/MOTS-CLÉS DE L'ENTREPRISE :\n{', '.join(keywords)}\n"

        prompt += f"\nMON PROFIL :\n{profile_text}\n"
        prompt += "\nMES PROJETS ET RÉALISATIONS CLÉS :\n"

        for i, proj in enumerate(project_highlights, 1):
            prompt += f"\n{i}. {proj['name']} :\n"
            for achievement in proj['achievements']:
                prompt += f"   - {achievement}\n"

        prompt += f"\nMES COMPÉTENCES TECHNIQUES : {', '.join(skills[:12])}\n"

        # Final instruction
        if job_title and company_name:
            prompt += f"\nRédigez un corps de lettre convaincant qui démontre pourquoi je suis le candidat idéal pour le poste de {job_title} chez {company_name}."
        elif job_title:
            prompt += f"\nRédigez un corps de lettre convaincant qui démontre pourquoi je suis le candidat idéal pour le poste de {job_title}."
        elif company_name:
            prompt += f"\nRédigez un corps de lettre convaincant qui démontre pourquoi je suis le candidat idéal pour ce poste chez {company_name}."
        else:
            prompt += "\nRédigez un corps de lettre convaincant qui démontre pourquoi je suis le candidat idéal pour cette opportunité."

    return prompt
