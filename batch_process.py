"""
Global Batch Processor
======================
Process multiple resumes in parallel with automatic error recovery and learning.
"""

import os
import json
import time
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from collections import defaultdict, Counter
import traceback

from src.core.parser import ResumeParser, ParsingResult
from src.core.section_learner import SectionLearner


class BatchProcessor:
    """
    Batch resume processing with:
    - Parallel processing
    - Automatic error recovery
    - Progress tracking
    - Quality analysis
    - Self-learning from patterns
    """
    
    def __init__(
        self,
        output_dir: str = "outputs/batch",
        config_path: Optional[str] = None,
        max_workers: Optional[int] = None
    ):
        """
        Initialize batch processor.
        
        Args:
            output_dir: Directory for output files
            config_path: Path to sections_database.json
            max_workers: Number of parallel workers (default: CPU count)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "sections_database.json"
        
        self.config_path = config_path
        self.max_workers = max_workers or max(1, os.cpu_count() - 1)
        self.learner = SectionLearner(str(config_path))
    
    def process_single(
        self,
        file_path: str,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Process a single resume (used by parallel workers).
        
        Returns:
            Result dictionary with status and data
        """
        try:
            parser = ResumeParser(config_path=str(self.config_path))
            result = parser.parse(file_path, verbose=verbose)
            
            return {
                'file': file_path,
                'success': result.success,
                'strategy': result.strategy_used.value if result.strategy_used else None,
                'quality': result.quality_score,
                'processing_time': result.processing_time,
                'data': result.data,
                'simplified': result.simplified_json,
                'warnings': result.warnings,
                'errors': result.errors
            }
            
        except Exception as e:
            return {
                'file': file_path,
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def process_batch(
        self,
        file_paths: List[str],
        save_individual: bool = True,
        save_summary: bool = True,
        enable_learning: bool = True,
        verbose: bool = False,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[str, Any]:
        """
        Process multiple resumes in parallel.
        
        Args:
            file_paths: List of resume file paths
            save_individual: Save individual JSON results
            save_summary: Save batch summary
            enable_learning: Enable self-learning from patterns
            verbose: Print progress
            progress_callback: Optional callback(completed, total)
            
        Returns:
            Batch processing summary
        """
        start_time = time.time()
        
        if verbose:
            print(f"\n{'='*70}")
            print(f"Batch Processor: {len(file_paths)} resumes")
            print(f"Workers: {self.max_workers}")
            print(f"Output: {self.output_dir}")
            print(f"{'='*70}\n")
        
        results = []
        completed = 0
        
        # Process in parallel
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all jobs
            future_to_file = {
                executor.submit(self.process_single, fp, False): fp
                for fp in file_paths
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                
                try:
                    result = future.result()
                    results.append(result)
                    completed += 1
                    
                    if verbose:
                        status = "✓" if result['success'] else "✗"
                        quality = result.get('quality', 0)
                        print(f"{status} [{completed}/{len(file_paths)}] {Path(file_path).name} (Q: {quality:.0f})")
                    
                    if progress_callback:
                        progress_callback(completed, len(file_paths))
                    
                except Exception as e:
                    if verbose:
                        print(f"✗ [{completed}/{len(file_paths)}] {Path(file_path).name} - Error: {e}")
                    
                    results.append({
                        'file': file_path,
                        'success': False,
                        'error': str(e)
                    })
                    completed += 1
        
        total_time = time.time() - start_time
        
        # Analyze results
        summary = self._generate_summary(results, total_time)
        
        # Save individual results
        if save_individual:
            self._save_individual_results(results)
        
        # Save summary
        if save_summary:
            summary_path = self.output_dir / "batch_summary.json"
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            if verbose:
                print(f"\nSummary saved to: {summary_path}")
        
        # Self-learning phase
        if enable_learning:
            self._learn_from_batch(results, verbose=verbose)
        
        if verbose:
            print(f"\n{'='*70}")
            print(f"Batch Complete!")
            print(f"  Success: {summary['statistics']['success_count']}/{len(file_paths)}")
            print(f"  Avg Quality: {summary['statistics']['avg_quality']:.1f}/100")
            print(f"  Total Time: {total_time:.1f}s")
            print(f"  Avg Time: {summary['statistics']['avg_time']:.2f}s/resume")
            print(f"{'='*70}\n")
        
        return summary
    
    def _generate_summary(
        self,
        results: List[Dict[str, Any]],
        total_time: float
    ) -> Dict[str, Any]:
        """Generate batch processing summary"""
        successful = [r for r in results if r.get('success')]
        failed = [r for r in results if not r.get('success')]
        
        # Statistics
        stats = {
            'total': len(results),
            'success_count': len(successful),
            'failed_count': len(failed),
            'success_rate': len(successful) / len(results) * 100 if results else 0,
            'total_time': total_time,
            'avg_time': total_time / len(results) if results else 0,
            'avg_quality': sum(r.get('quality', 0) for r in successful) / len(successful) if successful else 0
        }
        
        # Strategy distribution
        strategy_counts = Counter(r.get('strategy') for r in successful if r.get('strategy'))
        
        # Quality distribution
        quality_bins = {'excellent': 0, 'good': 0, 'fair': 0, 'poor': 0}
        for r in successful:
            q = r.get('quality', 0)
            if q >= 90:
                quality_bins['excellent'] += 1
            elif q >= 75:
                quality_bins['good'] += 1
            elif q >= 60:
                quality_bins['fair'] += 1
            else:
                quality_bins['poor'] += 1
        
        # Section distribution
        section_counts = Counter()
        for r in successful:
            sections = r.get('data', {}).get('sections', [])
            for section in sections:
                section_name = section.get('section', 'Unknown')
                section_counts[section_name] += 1
        
        # Error analysis
        error_types = Counter()
        for r in failed:
            error = r.get('error', 'Unknown error')
            # Categorize error
            if 'timeout' in error.lower():
                error_types['timeout'] += 1
            elif 'memory' in error.lower():
                error_types['memory'] += 1
            elif 'corrupt' in error.lower() or 'invalid' in error.lower():
                error_types['corrupt_file'] += 1
            else:
                error_types['other'] += 1
        
        return {
            'statistics': stats,
            'strategies': dict(strategy_counts),
            'quality_distribution': quality_bins,
            'section_distribution': dict(section_counts.most_common(20)),
            'error_analysis': dict(error_types),
            'failed_files': [r['file'] for r in failed],
            'results': results
        }
    
    def _save_individual_results(self, results: List[Dict[str, Any]]):
        """Save individual resume results"""
        individual_dir = self.output_dir / "individual"
        individual_dir.mkdir(exist_ok=True)
        
        for result in results:
            file_path = result['file']
            file_stem = Path(file_path).stem
            
            output_path = individual_dir / f"{file_stem}.json"
            
            # Simplified result (without full data)
            simplified = {
                'file': file_path,
                'success': result['success'],
                'strategy': result.get('strategy'),
                'quality': result.get('quality'),
                'processing_time': result.get('processing_time'),
                'sections': result.get('data', {}).get('sections', []),
                'contact': result.get('data', {}).get('contact', {}),
                'warnings': result.get('warnings', []),
                'errors': result.get('errors', [])
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(simplified, f, indent=2, ensure_ascii=False)
    
    def _learn_from_batch(self, results: List[Dict[str, Any]], verbose: bool = False):
        """
        Learn from batch results to improve section detection.
        
        Analyzes:
        - Unknown sections that appear frequently
        - Potential new section types
        - False positive patterns
        """
        if verbose:
            print("\n🧠 Learning from batch results...")
        
        # Collect all unknown sections
        unknown_sections = defaultdict(lambda: {'count': 0, 'context': []})
        
        for result in results:
            if not result.get('success'):
                continue
            
            sections = result.get('data', {}).get('sections', [])
            for section in sections:
                section_name = section.get('section', '')
                
                # Focus on "Unknown Sections"
                if section_name == 'Unknown Sections':
                    lines = section.get('lines', [])
                    
                    # Try to extract heading from first line
                    if lines:
                        potential_heading = lines[0]
                        
                        # Simple heuristic: if it's short and title-cased, might be a heading
                        if len(potential_heading) < 50 and potential_heading.istitle():
                            unknown_sections[potential_heading]['count'] += 1
                            unknown_sections[potential_heading]['context'].extend(lines[1:5])
        
        if not unknown_sections:
            if verbose:
                print("  No new sections discovered")
            return
        
        # Prepare for analysis
        headings_with_freq = [
            (heading, data['count'], data['context'])
            for heading, data in unknown_sections.items()
            if data['count'] >= 2  # Must appear in at least 2 resumes
        ]
        
        if not headings_with_freq:
            if verbose:
                print("  No frequent unknown sections found")
            return
        
        # Analyze with learner
        report = self.learner.analyze_batch_headings(
            headings_with_freq,
            auto_add=False  # Don't auto-add, require manual review
        )
        
        if verbose:
            if report['proposed_new']:
                print(f"\n  📋 Proposed new sections ({len(report['proposed_new'])}):")
                for prop in report['proposed_new'][:5]:
                    print(f"    - '{prop['heading']}' (freq: {prop['frequency']})")
            
            if report['false_positives']:
                print(f"\n  🚫 False positives detected ({len(report['false_positives'])}):")
                for fp in report['false_positives'][:5]:
                    print(f"    - '{fp['heading']}'")
        
        # Save learning report
        report_path = self.output_dir / "learning_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        if verbose:
            print(f"\n  Learning report saved to: {report_path}")


def main():
    """Example usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch resume processor with self-learning")
    parser.add_argument("--input", required=True, help="Input directory or file pattern")
    parser.add_argument("--output", default="outputs/batch", help="Output directory")
    parser.add_argument("--workers", type=int, help="Number of parallel workers")
    parser.add_argument("--no-learning", action="store_true", help="Disable self-learning")
    parser.add_argument("--quiet", action="store_true", help="Quiet mode")
    
    args = parser.parse_args()
    
    # Collect files
    input_path = Path(args.input)
    if input_path.is_file():
        files = [str(input_path)]
    elif input_path.is_dir():
        files = [
            str(f) for f in input_path.rglob("*")
            if f.suffix.lower() in ['.pdf', '.docx']
        ]
    else:
        # Glob pattern
        files = [str(f) for f in Path.cwd().glob(args.input)]
    
    if not files:
        print(f"No files found matching: {args.input}")
        return
    
    # Process batch
    processor = BatchProcessor(
        output_dir=args.output,
        max_workers=args.workers
    )
    
    summary = processor.process_batch(
        file_paths=files,
        save_individual=True,
        save_summary=True,
        enable_learning=not args.no_learning,
        verbose=not args.quiet
    )
    
    # Print summary
    if not args.quiet:
        print("\n📊 Summary:")
        print(f"  Total: {summary['statistics']['total']}")
        print(f"  Success: {summary['statistics']['success_count']} ({summary['statistics']['success_rate']:.1f}%)")
        print(f"  Quality: {summary['statistics']['avg_quality']:.1f}/100")
        print(f"  Time: {summary['statistics']['total_time']:.1f}s")


if __name__ == "__main__":
    main()
