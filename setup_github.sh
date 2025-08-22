#!/bin/bash

# GitHub Repository Setup Script
# Run this after authenticating with: gh auth login

echo "Creating GitHub repository for Trust Document Summarizer..."

# Create the repository
gh repo create trust-document-summarizer \
  --public \
  --description "AI-powered system for analyzing and summarizing trust documents with accurate citation tracking" \
  --source=. \
  --remote=origin \
  --push

echo "Repository created and pushed successfully!"
echo ""
echo "Your repository is now available at:"
echo "https://github.com/$(gh api user --jq .login)/trust-document-summarizer"
echo ""
echo "Next steps:"
echo "1. Add collaborators: gh repo edit --add-collaborator USERNAME"
echo "2. Set up GitHub Pages: gh repo edit --enable-pages"
echo "3. Create issues: gh issue create --title 'Issue title' --body 'Issue description'"