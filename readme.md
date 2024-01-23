# Planda

## Generate a health insurance plan microsite with LLMs

### Usage

```
python3 main.py <pdf_path> <plan_name> <site_dir>
```

Where pdf_path is the path to the Summary of Benefits and Coverage (SBC) PDF, plan_name is the name of the insurance plan, and site_dir is the output directory for the webpage and associated files.

Note: You will need a working OpenAI API key in your bash profile that can access GPT-4V

### Roadmap
* Handle missing values gracefully
* Pull in additional file types, like formulary and plan handbook
* Work for batches of files across many plans