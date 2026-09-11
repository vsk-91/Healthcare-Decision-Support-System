"""
Django management command: train_ml_model

Usage:
    python manage.py train_ml_model
    python manage.py train_ml_model --dataset /path/to/custom.csv

Description:
    Trains Logistic Regression, Decision Tree, and Random Forest classifiers
    on the clinical symptoms dataset, evaluates all three models, selects the
    best based on weighted F1-score, and saves it to ai_engine/ml_models/best_model.pkl.

    After running this command, the ML model will be automatically used by
    MultimodalAnalysisService.analyze() for condition prediction instead of
    the keyword-based fallback.

    No external APIs or internet connection required.
    Works independently of the Gemini API (local sklearn training, no API calls).
"""

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Train Logistic Regression, Decision Tree, and Random Forest classifiers "
        "on the clinical symptoms dataset. Selects and saves the best model "
        "(by weighted F1-score) for use in the AI analysis pipeline."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dataset",
            type=str,
            default=None,
            help=(
                "Path to a custom training CSV dataset "
                "(default: ai_engine/ml_data/clinical_symptoms_dataset.csv)"
            ),
        )

    def handle(self, *args, **options):
        from pathlib import Path

        # Allow custom dataset override
        custom_dataset = options.get("dataset")
        if custom_dataset:
            from ai_engine.services import ml_predictor as ml_mod
            ml_mod._DATASET_PATH = Path(custom_dataset)
            self.stdout.write(f"Using custom dataset: {custom_dataset}")

        self.stdout.write(self.style.MIGRATE_HEADING(
            "\nHealthcare DSS — ML Classifier Training\n" + "=" * 55
        ))

        try:
            from ai_engine.services.ml_predictor import MLPredictor
            predictor = MLPredictor()
            report = predictor.train()
        except FileNotFoundError as exc:
            raise CommandError(
                f"{exc}\n\n"
                "Generate the dataset first:\n"
                "  python ai_engine/ml_data/generate_dataset.py"
            )
        except Exception as exc:
            raise CommandError(f"Training failed: {exc}")

        # ---- Print comparison table ----
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Model Comparison (20% Stratified Test Split)"))
        self.stdout.write("=" * 75)
        header = f"{'Algorithm':<28}  {'Accuracy':>8}  {'Precision':>9}  {'Recall':>7}  {'F1 (W)':>7}  {'CV F1':>10}"
        self.stdout.write(header)
        self.stdout.write("-" * 75)

        for name, metrics in report["all_models"].items():
            is_best = (name == report["selected_algorithm"])
            row = (
                f"{'* ' + name if is_best else '  ' + name:<28}  "
                f"{metrics['accuracy']:>8.4f}  "
                f"{metrics['precision']:>9.4f}  "
                f"{metrics['recall']:>7.4f}  "
                f"{metrics['f1_weighted']:>7.4f}  "
                f"{metrics['cv_f1_mean']:>6.4f}±{metrics['cv_f1_std']:.4f}"
            )
            if is_best:
                self.stdout.write(self.style.SUCCESS(row))
            else:
                self.stdout.write(row)

        self.stdout.write("-" * 75)
        self.stdout.write("  (* = selected model)")

        # ---- Per-class metrics for best model ----
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"Per-Class Metrics — {report['selected_algorithm']}"
        ))
        self.stdout.write("=" * 75)
        self.stdout.write(f"{'Class':<42}  {'Precision':>9}  {'Recall':>7}  {'F1':>6}  {'Support':>7}")
        self.stdout.write("-" * 75)

        best_report = report["all_models"][report["selected_algorithm"]]
        for cls, metrics in best_report.get("per_class", {}).items():
            if cls in ("accuracy", "macro avg", "weighted avg"):
                continue
            support = int(metrics.get("support", 0))
            row = (
                f"{cls:<42}  "
                f"{metrics.get('precision', 0):>9.4f}  "
                f"{metrics.get('recall', 0):>7.4f}  "
                f"{metrics.get('f1-score', 0):>6.4f}  "
                f"{support:>7}"
            )
            self.stdout.write(row)

        # Weighted avg row
        wavg = best_report.get("per_class", {}).get("weighted avg", {})
        if wavg:
            self.stdout.write("-" * 75)
            self.stdout.write(
                f"{'Weighted Average':<42}  "
                f"{wavg.get('precision', 0):>9.4f}  "
                f"{wavg.get('recall', 0):>7.4f}  "
                f"{wavg.get('f1-score', 0):>6.4f}  "
                f"{int(wavg.get('support', 0)):>7}"
            )

        # ---- Summary ----
        self.stdout.write("")
        self.stdout.write("=" * 55)
        best_m = report["best_metrics"]
        self.stdout.write(self.style.SUCCESS("TRAINING SUMMARY"))
        self.stdout.write("=" * 55)
        self.stdout.write(f"Selected algorithm : {report['selected_algorithm']}")
        self.stdout.write(f"Dataset rows       : {report['dataset_rows']} ({report['train_rows']} train / {report['test_rows']} test)")
        self.stdout.write(f"Features           : {report['n_features']} ({len([f for f in report.get('classes', [])])} classes: {', '.join(report['classes'][:3])}...)")
        self.stdout.write(f"Test accuracy      : {best_m['accuracy']:.4f}")
        self.stdout.write(f"Test F1 (weighted) : {best_m['f1_weighted']:.4f}")
        self.stdout.write(f"CV F1 (5-fold)     : {best_m['cv_f1_mean']:.4f} ± {best_m['cv_f1_std']:.4f}")
        self.stdout.write(f"Model saved        : {report['model_path']}")
        self.stdout.write(f"Report saved       : {report['model_path'].replace('best_model.pkl', 'training_report.json')}")
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            "ML model trained and saved. "
            "It will be used automatically in MultimodalAnalysisService.analyze()."
        ))
