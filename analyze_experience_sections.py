"""
Analyze how NER model handles 50 experience sections
This helps understand model behavior and grouping issues
"""

import pandas as pd
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from transformers.utils import logging as transformers_logging
import json

# Suppress transformers logging
transformers_logging.set_verbosity_error()


def analyze_experience_section(ner_pipeline, text: str, index: int):
    """Analyze a single experience section"""
    
    if not text or pd.isna(text) or len(text.strip()) < 20:
        return None
    
    # Truncate if too long (take first 1000 chars for analysis)
    text = text[:1000]
    
    print(f"\n{'='*100}")
    print(f"SAMPLE {index + 1}")
    print(f"{'='*100}")
    print(f"\nText (first 300 chars):\n{text[:300]}...")
    
    # Run NER
    try:
        entities = ner_pipeline(text)
    except Exception as e:
        print(f"❌ Error running NER: {e}")
        return None
    
    if not entities:
        print("❌ No entities found")
        return None
    
    # Show entities
    print(f"\n📊 Found {len(entities)} entities:")
    print(f"\n{'Text':<40} | {'Type':<10} | {'Score':<6} | {'Position':<10}")
    print("-" * 100)
    
    for entity in entities:
        print(f"{entity['word'][:40]:<40} | "
              f"{entity['entity_group']:<10} | "
              f"{entity['score']:.3f}  | "
              f"{entity['start']}-{entity['end']}")
    
    # Analyze patterns
    analysis = {
        'total_entities': len(entities),
        'companies': [e for e in entities if e['entity_group'] == 'COMPANY'],
        'roles': [e for e in entities if e['entity_group'] == 'ROLE'],
        'dates': [e for e in entities if e['entity_group'] == 'DATE'],
        'techs': [e for e in entities if e['entity_group'] == 'TECH'],
    }
    
    print(f"\n📈 Summary:")
    print(f"   Companies: {len(analysis['companies'])}")
    print(f"   Roles:     {len(analysis['roles'])}")
    print(f"   Dates:     {len(analysis['dates'])}")
    print(f"   Tech:      {len(analysis['techs'])}")
    
    # Check for fragmentation issues
    fragmented_companies = []
    for i, comp in enumerate(analysis['companies']):
        if '##' in comp['word'] or len(comp['word'].strip()) < 3:
            fragmented_companies.append(comp)
    
    if fragmented_companies:
        print(f"\n⚠️  Found {len(fragmented_companies)} potentially fragmented company names:")
        for comp in fragmented_companies:
            print(f"     '{comp['word']}' (score: {comp['score']:.3f})")
    
    return analysis


def main():
    print("="*100)
    print("🔬 ANALYZING NER MODEL BEHAVIOR ON 50 EXPERIENCE SECTIONS")
    print("="*100)
      # Load CSV
    print("\n⏳ Loading experience sections from CSV...")
    
    # Try different encodings
    csv_path = 'outputs/batch_sections_4 1(Sections).csv'
    df = None
    
    for encoding in ['latin-1', 'cp1252', 'iso-8859-1', 'utf-8', 'utf-16']:
        try:
            df = pd.read_csv(csv_path, encoding=encoding)
            print(f"✅ Loaded {len(df)} rows (encoding: {encoding})")
            break
        except (UnicodeDecodeError, UnicodeError) as e:
            print(f"   ⚠️  {encoding} encoding failed, trying next...")
            continue
        except Exception as e:
            print(f"   ❌ Failed with {encoding}: {e}")
            continue
    
    if df is None:
        print("❌ Could not load CSV with any encoding")
        print("💡 Try converting the CSV to UTF-8 first or use a different file")
        return
    
    # Filter rows with experience sections
    df_with_exp = df[df['Experience'].notna() & (df['Experience'].str.len() > 50)]
    print(f"✅ Found {len(df_with_exp)} rows with experience sections")
    
    # Take 50 samples
    sample_size = min(50, len(df_with_exp))
    samples = df_with_exp.head(sample_size)
    print(f"✅ Analyzing {sample_size} samples\n")
    
    # Load NER model
    print("⏳ Loading NER model...")
    model_path = "ml_model"
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForTokenClassification.from_pretrained(model_path)
    ner_pipeline = pipeline(
        "ner", 
        model=model, 
        tokenizer=tokenizer, 
        aggregation_strategy="simple"
    )
    print("✅ Model loaded\n")
    
    # Analyze each sample
    results = []
    for idx, row in samples.iterrows():
        experience_text = row['Experience']
        analysis = analyze_experience_section(ner_pipeline, experience_text, idx)
        
        if analysis:
            results.append({
                'index': idx,
                'pdf_path': row.get('pdf_path', 'Unknown'),
                'analysis': analysis
            })
    
    # Overall statistics
    print("\n" + "="*100)
    print("📊 OVERALL STATISTICS")
    print("="*100)
    
    total_samples = len(results)
    total_companies = sum(len(r['analysis']['companies']) for r in results)
    total_roles = sum(len(r['analysis']['roles']) for r in results)
    total_dates = sum(len(r['analysis']['dates']) for r in results)
    total_techs = sum(len(r['analysis']['techs']) for r in results)
    
    print(f"\nAnalyzed:           {total_samples} samples")
    print(f"Total Companies:    {total_companies} ({total_companies/total_samples:.1f} avg per resume)")
    print(f"Total Roles:        {total_roles} ({total_roles/total_samples:.1f} avg per resume)")
    print(f"Total Dates:        {total_dates} ({total_dates/total_samples:.1f} avg per resume)")
    print(f"Total Tech:         {total_techs} ({total_techs/total_samples:.1f} avg per resume)")
    
    # Check fragmentation rate
    fragmented_count = 0
    for r in results:
        for comp in r['analysis']['companies']:
            if '##' in comp['word'] or len(comp['word'].strip()) < 3:
                fragmented_count += 1
    
    fragmentation_rate = (fragmented_count / total_companies * 100) if total_companies > 0 else 0
    print(f"\n⚠️  Fragmentation:")
    print(f"   Fragmented companies: {fragmented_count}/{total_companies} ({fragmentation_rate:.1f}%)")
    
    # Common issues
    print(f"\n🔍 Common Patterns:")
    
    # Low confidence companies
    low_conf_companies = []
    for r in results:
        for comp in r['analysis']['companies']:
            if comp['score'] < 0.7:
                low_conf_companies.append(comp)
    
    print(f"   Low confidence (<0.7) companies: {len(low_conf_companies)}")
    
    # Single character entities
    single_char = []
    for r in results:
        for entity in (r['analysis']['companies'] + r['analysis']['roles'] + 
                      r['analysis']['dates'] + r['analysis']['techs']):
            if len(entity['word'].strip()) == 1:
                single_char.append(entity)
    
    print(f"   Single character entities: {len(single_char)}")
    
    print("\n" + "="*100)
    print("✅ ANALYSIS COMPLETE")
    print("="*100)
    
    # Save detailed results
    output_file = "outputs/ner_analysis_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n💾 Detailed results saved to: {output_file}")


if __name__ == "__main__":
    main()
