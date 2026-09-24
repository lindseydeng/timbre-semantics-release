"""Command line interface. Run from the repository root or pass explicit paths."""

import argparse

from .design import MODELS, load_design, scan_audio


def main():
    parser = argparse.ArgumentParser(prog="timbre")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="Check the experiment 2 audio inventory")
    validate.add_argument(
        "--data-root", required=True, help="Explicit location of the audio to inspect"
    )
    validate.add_argument("--config", default="configs/experiment2.json")
    analyze = commands.add_parser("analyze", help="Recompute experiment 2 statistics from CSVs")
    analyze.add_argument("--input", default="results/reference/experiment2")
    analyze.add_argument("--output", default="outputs/analysis")
    analyze.add_argument("--config", default="configs/experiment2.json")
    paper = commands.add_parser(
        "paper", help="Generate paper tables and figures from saved scores; no inference"
    )
    paper.add_argument("--reference", default="results/reference")
    paper.add_argument("--output", default="outputs/paper")
    paper.add_argument("--config", default="configs/experiment2.json")
    paper.add_argument(
        "--figures", action="store_true", help="Render figures (requires the paper extra)"
    )
    for number in (1, 2):
        sub = commands.add_parser(f"experiment{number}", help=f"Run experiment {number} inference")
        sub.add_argument("--model", choices=MODELS, required=True)
        sub.add_argument(
            "--data-root", required=True, help="Explicit location of the actual experiment inputs"
        )
        sub.add_argument("--output", required=True, help="New or empty output directory")
        sub.add_argument("--batch-size", type=int, default=16)
        if number == 2:
            sub.add_argument("--config", default="configs/experiment2.json")
    args = parser.parse_args()
    if args.command == "validate":
        originals, frame = scan_audio(args.data_root, load_design(args.config))
        print(
            f"Filename/condition inventory: {len(originals)} originals and {len(frame)} manipulated clips. "
            "This does not establish that these are the paper's actual waveforms."
        )
    elif args.command == "paper":
        from .paper import reproduce_paper

        output = reproduce_paper(args.reference, args.output, args.config, figures=args.figures)
        print(
            f"Saved-score tables written to {output}. "
            "No model inference or original-audio validation was performed."
        )
    elif args.command == "analyze":
        from .analysis import analyze_experiment2

        print(analyze_experiment2(args.input, args.output, load_design(args.config)).to_string())
    else:
        from .experiments import run_experiment1, run_experiment2

        if args.batch_size < 1:
            parser.error("--batch-size must be positive")
        if args.command == "experiment1":
            run_experiment1(args.model, args.data_root, args.output, args.batch_size)
        else:
            run_experiment2(
                args.model, args.data_root, args.output, load_design(args.config), args.batch_size
            )


if __name__ == "__main__":
    main()
