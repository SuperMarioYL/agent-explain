Output assets/demo.gif

Set Width 1200
Set Height 600
Set FontSize 16
Set Padding 20
Set Theme Dracula

# Show the sample plan
Type "cat examples/plan.md"
Enter
Sleep 2s

# Run EXPLAIN — the aha moment: per-step projection table
Type "agent-explain examples/plan.md"
Enter
Sleep 3s

# JSON output for piping into a pre-approval gate
Type "agent-explain examples/plan.md --json"
Enter
Sleep 2s

# Filter totals with jq
Type "agent-explain examples/plan.md --json | jq .totals"
Enter
Sleep 2s
