// Command check-layers checks that every layer in a go-arch-lint file says
// what it is for and has been reviewed recently enough.
//
// Each component under "components:" must carry two comment lines above it:
//
//	# purpose: One sentence on what belongs in this layer.
//	# reviewed: <commit>
//
// The reviewed commit is where someone last confirmed that the purpose and the
// layer's packages still match. Once more than --limit commits have touched
// the layer's packages since then, the layer is stale. With --base, a stale
// layer fails only when the current branch changes it, so a pull request
// fails only for the layers it touches.
//
// Run it from the repository root with the standard library alone:
//
//	go run path/to/check-layers.go --base origin/main
//
// It needs the full Git history of the layers' packages; in CI, check out
// with fetch-depth: 0.
package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
)

const usage = `Usage: go run check-layers.go [flags]

Checks the "# purpose:" and "# reviewed:" lines of every component in a
go-arch-lint file, and fails a layer once more than --limit commits have
changed its packages since its reviewed commit.

To clear a stale layer: read its purpose and its packages, and the commits
and files this check lists. If the purpose still describes every package,
set "# reviewed:" to the commit it prints. If not, fix the purpose or the
component's "in:" list (or split or merge layers) first, then set it.

Flags:
`

// maxShown caps the commits and files printed as evidence for one layer.
const maxShown = 20

type layer struct {
	name     string
	line     int
	purpose  string
	reviewed string
	dirs     []string
}

func main() {
	flag.Usage = func() {
		fmt.Fprint(os.Stderr, usage)
		flag.PrintDefaults()
	}
	archFile := flag.String("arch-file", ".go-arch-lint.yml", "go-arch-lint file to check")
	limit := flag.Int("limit", 50, "commits to a layer's packages allowed since its reviewed commit")
	base := flag.String("base", "", "base branch of the pull request; when set, only layers the branch changes can fail")
	linter := flag.String("go-arch-lint", "go run github.com/fe3dback/go-arch-lint@v1.19.1", "command that runs go-arch-lint")
	flag.Parse()

	failed, err := run(*archFile, *limit, *base, *linter)
	if err != nil {
		fmt.Fprintln(os.Stderr, "check-layers:", err)
		os.Exit(2)
	}
	if failed {
		os.Exit(1)
	}
}

func run(archFile string, limit int, base, linter string) (bool, error) {
	layers, err := readLayers(archFile)
	if err != nil {
		return false, err
	}
	if err := mapDirs(layers, archFile, linter); err != nil {
		return false, err
	}
	// A new marker names a commit on the base branch, because a squash merge
	// drops the branch's own commits.
	head, err := git("rev-parse", "--short", "HEAD")
	if err != nil {
		return false, err
	}
	var changed []string
	if base != "" {
		out, err := git("diff", "--name-only", base+"...HEAD")
		if err != nil {
			return false, fmt.Errorf("diff against %s: %w (in CI, check out with fetch-depth: 0)", base, err)
		}
		changed = lines(out)
		if head, err = git("rev-parse", "--short", base); err != nil {
			return false, err
		}
	}

	failed := false
	for _, l := range layers {
		where := fmt.Sprintf("%s:%d: layer %q", archFile, l.line, l.name)
		if l.purpose == "" {
			fmt.Printf("%s has no \"# purpose:\" line. Add one above it saying what belongs in the layer.\n", where)
			failed = true
		}
		if l.reviewed == "" {
			fmt.Printf("%s has no \"# reviewed:\" line. Once its purpose matches its packages, add \"# reviewed: %s\".\n", where, head)
			failed = true
			continue
		}
		if _, err := git("rev-parse", "--verify", "--quiet", l.reviewed+"^{commit}"); err != nil {
			fmt.Printf("%s is reviewed at %s, which isn't a commit in this checkout. Fix the line, or fetch the full history (fetch-depth: 0 in CI).\n", where, l.reviewed)
			failed = true
			continue
		}
		if len(l.dirs) == 0 {
			continue
		}
		specs := pathspecs(l.dirs)
		count, err := git(append([]string{"rev-list", "--count", l.reviewed + "..HEAD", "--"}, specs...)...)
		if err != nil {
			return false, err
		}
		var n int
		fmt.Sscan(count, &n)
		if n <= limit {
			continue
		}
		if base != "" && !touches(changed, l.dirs) {
			continue
		}
		failed = true
		if err := report(where, l, n, limit, head, specs); err != nil {
			return false, err
		}
	}
	if !failed {
		fmt.Printf("check-layers: %d layers have a purpose and a recent review.\n", len(layers))
	}
	return failed, nil
}

func report(where string, l layer, n, limit int, head string, specs []string) error {
	fmt.Printf("%s has had %d commits to its packages since it was reviewed at %s (limit %d).\n", where, n, l.reviewed, limit)
	fmt.Printf("  purpose: %s\n", l.purpose)
	fmt.Printf("  packages: %s\n", strings.Join(l.dirs, ", "))
	commits, err := git(append([]string{"log", "--oneline", "--no-decorate", "-n", fmt.Sprint(maxShown), l.reviewed + "..HEAD", "--"}, specs...)...)
	if err != nil {
		return err
	}
	fmt.Printf("  commits since then (newest %d):\n", min(n, maxShown))
	for _, c := range lines(commits) {
		fmt.Printf("    %s\n", c)
	}
	files, err := git(append([]string{"diff", "--name-status", "--diff-filter=AD", l.reviewed, "HEAD", "--"}, specs...)...)
	if err != nil {
		return err
	}
	var fl []string
	for _, f := range lines(files) {
		if !strings.HasSuffix(f, "_test.go") {
			fl = append(fl, f)
		}
	}
	if len(fl) > 0 {
		fmt.Println("  files added (A) or deleted (D) since then:")
		for i, f := range fl {
			if i == maxShown {
				fmt.Printf("    ... and %d more\n", len(fl)-maxShown)
				break
			}
			fmt.Printf("    %s\n", strings.ReplaceAll(f, "\t", " "))
		}
	}
	fmt.Printf("  If the purpose still describes every package, set \"# reviewed: %s\". If not, fix the purpose or the layer's packages first.\n", head)
	return nil
}

var (
	keyLine     = regexp.MustCompile(`^(\s*)([A-Za-z0-9_.-]+)\s*:`)
	purposeLine = regexp.MustCompile(`^\s*#\s*purpose:\s*(.*?)\s*$`)
	reviewLine  = regexp.MustCompile(`^\s*#\s*reviewed:\s*(\S*)\s*$`)
)

// readLayers reads each component's name and the purpose and reviewed comments
// above it. go-arch-lint drops comments, so this reads the file's lines.
func readLayers(path string) ([]layer, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var layers []layer
	var purpose, reviewed string
	inComponents := false
	indent := -1
	sc := bufio.NewScanner(bytes.NewReader(data))
	for n := 1; sc.Scan(); n++ {
		text := sc.Text()
		if strings.TrimSpace(text) == "" {
			continue
		}
		if m := keyLine.FindStringSubmatch(text); m != nil && m[1] == "" {
			inComponents = m[2] == "components"
			purpose, reviewed = "", ""
			continue
		}
		if !inComponents {
			continue
		}
		if m := purposeLine.FindStringSubmatch(text); m != nil {
			purpose = m[1]
			continue
		}
		if m := reviewLine.FindStringSubmatch(text); m != nil {
			reviewed = m[1]
			continue
		}
		m := keyLine.FindStringSubmatch(text)
		if m == nil {
			continue
		}
		if indent < 0 {
			indent = len(m[1])
		}
		if len(m[1]) != indent {
			continue
		}
		layers = append(layers, layer{name: m[2], line: n, purpose: purpose, reviewed: reviewed})
		purpose, reviewed = "", ""
	}
	if err := sc.Err(); err != nil {
		return nil, err
	}
	if len(layers) == 0 {
		return nil, fmt.Errorf("%s has no components", path)
	}
	return layers, nil
}

// mapDirs asks go-arch-lint which files each component holds, so the check
// follows the same globs the linter does, and records each layer's directories.
func mapDirs(layers []layer, archFile, linter string) error {
	args := append(strings.Fields(linter), "mapping", "--json", "--arch-file", archFile)
	cmd := exec.Command(args[0], args[1:]...)
	var stderr bytes.Buffer
	cmd.Stderr = &stderr
	out, err := cmd.Output()
	if err != nil {
		return fmt.Errorf("%s: %w\n%s", strings.Join(args, " "), err, stderr.String())
	}
	var mapping struct {
		Payload struct {
			ProjectDirectory string
			MappingList      []struct{ FileName, ComponentName string }
		}
	}
	if err := json.Unmarshal(out, &mapping); err != nil {
		return fmt.Errorf("reading go-arch-lint mapping: %w", err)
	}
	dirs := map[string]map[string]bool{}
	for _, f := range mapping.Payload.MappingList {
		rel, err := filepath.Rel(mapping.Payload.ProjectDirectory, filepath.Dir(f.FileName))
		if err != nil {
			return err
		}
		if dirs[f.ComponentName] == nil {
			dirs[f.ComponentName] = map[string]bool{}
		}
		dirs[f.ComponentName][filepath.ToSlash(rel)] = true
	}
	for i := range layers {
		for d := range dirs[layers[i].name] {
			layers[i].dirs = append(layers[i].dirs, d)
		}
		sort.Strings(layers[i].dirs)
	}
	return nil
}

// pathspecs matches the files directly inside each directory: a Go package is
// one directory, and its subdirectories are other packages.
func pathspecs(dirs []string) []string {
	specs := make([]string, len(dirs))
	for i, d := range dirs {
		if d == "." {
			specs[i] = ":(glob)*"
		} else {
			specs[i] = ":(glob)" + d + "/*"
		}
	}
	return specs
}

func touches(changed, dirs []string) bool {
	in := map[string]bool{}
	for _, d := range dirs {
		in[d] = true
	}
	for _, f := range changed {
		if in[filepath.ToSlash(filepath.Dir(f))] {
			return true
		}
	}
	return false
}

func git(args ...string) (string, error) {
	cmd := exec.Command("git", args...)
	var stderr bytes.Buffer
	cmd.Stderr = &stderr
	out, err := cmd.Output()
	if err != nil {
		var exit *exec.ExitError
		if errors.As(err, &exit) && stderr.Len() > 0 {
			return "", fmt.Errorf("git %s: %s", strings.Join(args, " "), strings.TrimSpace(stderr.String()))
		}
		return "", fmt.Errorf("git %s: %w", strings.Join(args, " "), err)
	}
	return strings.TrimSpace(string(out)), nil
}

func lines(s string) []string {
	if s == "" {
		return nil
	}
	return strings.Split(s, "\n")
}
