#!/usr/bin/env python3
"""
NexusAGI Multi-Domain Demo
Test the AGI's ability to adapt to different domains
"""

import asyncio
import sys
from pathlib import Path

# Add core to path
sys.path.insert(0, str(Path(__file__).parent))

from core.domain_adaptor import DomainAdaptor


async def test_domain_detection():
    """Test auto-domain detection capabilities"""
    adaptor = DomainAdaptor()
    
    print("\n" + "="*70)
    print("  NexusAGI Multi-Domain Adaptation Test")
    print("="*70)
    
    test_inputs = [
        # Customer Support
        ("My order hasn't arrived yet. Can you help me track it?", "customer_support"),
        ("I want to return a product I bought last week", "customer_support"),
        ("What payment methods do you accept?", "customer_support"),
        
        # Research Assistant
        ("I need to write a literature review on machine learning", "research_assistant"),
        ("Can you explain qualitative vs quantitative research methods?", "research_assistant"),
        ("How do I cite sources in APA format?", "research_assistant"),
        
        # Health Advisor
        ("I've been having headaches lately, what could cause this?", "health_advisor"),
        ("What are some tips for better sleep?", "health_advisor"),
        ("How much water should I drink daily?", "health_advisor"),
        
        # Education Tutor
        ("Can you help me understand algebra?", "education_tutor"),
        ("What are good study strategies for exams?", "education_tutor"),
        ("Explain the scientific method to me", "education_tutor"),
        
        # Code Assistant
        ("I have a bug in my Python code, can you help debug?", "code_assistant"),
        ("What's the best way to handle errors in programming?", "code_assistant"),
        ("Explain object-oriented programming concepts", "code_assistant"),
        
        # Business Consulting
        ("I want to start a startup, what should I consider?", "business_consulting"),
        ("How do I create a business plan?", "business_consulting"),
        ("What metrics should I track for my business?", "business_consulting"),
        
        # Creative Writing
        ("Write me a short story about a robot", "creative_writing"),
        ("Help me write a poem about nature", "creative_writing"),
        ("I need ideas for a novel plot", "creative_writing"),
        
        # General Knowledge
        ("What is the meaning of life?", "general_knowledge"),
        ("Tell me an interesting fact", "general_knowledge"),
        ("What are your capabilities?", "general_knowledge"),
    ]
    
    print("\nTesting Domain Detection:\n")
    
    correct = 0
    total = len(test_inputs)
    
    for user_input, expected_domain in test_inputs:
        adaptation = await adaptor.adapt_to_input(user_input)
        detected = adaptation['domain']
        confidence = adaptation['confidence']
        
        status = "✓" if detected == expected_domain else "✗"
        if detected == expected_domain:
            correct += 1
        
        print(f"{status} [{detected:20s}] ({confidence:.2f}) {user_input[:50]}...")
    
    print(f"\n{'='*70}")
    print(f"Accuracy: {correct}/{total} ({correct/total*100:.1f}%)")
    print(f"{'='*70}")
    
    # Show domain statistics
    print("\nDomain Statistics:")
    stats = adaptor.get_statistics()
    for domain, info in stats['domain_stats'].items():
        if info['interaction_count'] > 0:
            print(f"  {domain}: {info['interaction_count']} interactions")


async def test_domain_knowledge():
    """Test domain-specific knowledge loading"""
    adaptor = DomainAdaptor()
    
    print("\n" + "="*70)
    print("  Domain Knowledge Test")
    print("="*70)
    
    domains = adaptor.get_available_domains()
    
    for domain in domains:
        print(f"\n{domain['display_name']}:")
        print(f"  Description: {domain['description']}")
        print(f"  Specializations: {', '.join(domain['specializations'])}")
    
    # Test loading domain knowledge
    test_query = "What is your shipping policy?"
    adaptation = await adaptor.adapt_to_input(test_query)
    
    print(f"\n\nQuery: '{test_query}'")
    print(f"Detected Domain: {adaptation['domain_name']}")
    print(f"Confidence: {adaptation['confidence']:.2f}")
    print(f"Response Style: {adaptation['response_style']}")


async def test_response_enhancement():
    """Test domain-specific response formatting"""
    adaptor = DomainAdaptor()
    
    print("\n" + "="*70)
    print("  Response Enhancement Test")
    print("="*70)
    
    test_cases = [
        ("I want to return my order", "We accept returns within 30 days. Please contact support."),
        ("I have a headache", "Headaches can be caused by dehydration, stress, or lack of sleep. Drink water and rest."),
        ("Help me with Python code", "Here's a solution: def hello(): print('Hello World')"),
    ]
    
    for user_input, base_response in test_cases:
        adaptation = await adaptor.adapt_to_input(user_input)
        enhanced = await adaptor.enhance_response(base_response, adaptation)
        
        print(f"\nInput: {user_input}")
        print(f"Domain: {adaptation['domain_name']}")
        print(f"Base Response: {base_response}")
        print(f"Enhanced Response: {enhanced}")


async def main():
    """Run all tests"""
    print("\n🧠 NexusAGI Multi-Domain System Test Suite")
    print("=" * 70)
    
    await test_domain_detection()
    await test_domain_knowledge()
    await test_response_enhancement()
    
    print("\n" + "="*70)
    print("  All tests completed!")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())