using System.Text.Json;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;

// 常驻分析器只建立内存编译，不执行项目的 MSBuild 任务或生成业务程序集。
var analyzer = new Analyzer();
Console.InputEncoding = System.Text.Encoding.UTF8;
Console.OutputEncoding = System.Text.Encoding.UTF8;
while (Console.ReadLine() is { } line)
{
    try { Console.WriteLine(JsonSerializer.Serialize(analyzer.Run(JsonDocument.Parse(line).RootElement))); }
    catch (Exception error) { Console.WriteLine(JsonSerializer.Serialize(new { error = error.Message })); }
}

sealed class ProjectState
{
    public string Version = "";
    public string ParseVersion = "";
    public CSharpCompilation Compilation = null!;
    public readonly Dictionary<string, (string Version, SyntaxTree Tree)> Trees = new();
    public List<(SyntaxNode Node, IMethodSymbol? Target, SymbolInfo Info, SemanticModel Model)> Calls = new();
}

sealed class Analyzer
{
    readonly Dictionary<string, ProjectState> projects = new();
    readonly List<string> order = new();
    readonly MetadataReference[] framework = ((string)AppContext.GetData("TRUSTED_PLATFORM_ASSEMBLIES")!)
        .Split(Path.PathSeparator).Select(path => MetadataReference.CreateFromFile(path)).ToArray();
    static string Text(JsonElement value, string name) => value.GetProperty(name).GetString()!;
    static object Location(ISymbol symbol) => new {
        symbol = symbol.ToDisplayString(SymbolDisplayFormat.CSharpErrorMessageFormat),
        kind = symbol.Kind.ToString(),
        declarations = symbol.Locations.Where(loc => loc.IsInSource).Select(loc => {
            var span = loc.GetLineSpan();
            var syntax = symbol.DeclaringSyntaxReferences.FirstOrDefault(r => r.SyntaxTree == loc.SourceTree)?.GetSyntax();
            var full = syntax?.GetLocation().GetLineSpan() ?? span;
            return new { path = span.Path, start_line = full.StartLinePosition.Line + 1, end_line = full.EndLinePosition.Line + 1 };
        }).ToArray()
    };
    static bool Same(IMethodSymbol? first, IMethodSymbol? second) => first != null && second != null &&
        SymbolEqualityComparer.Default.Equals(first.OriginalDefinition, second.OriginalDefinition);

    public object Run(JsonElement request)
    {
        if (request.TryGetProperty("action", out var action) && action.GetString() == "syntax")
        {
            var syntax = CSharpSyntaxTree.ParseText(Text(request, "content"), path: Text(request, "path"));
            var symbols = syntax.GetRoot().DescendantNodes().Select(node => {
                var name = node switch { BaseTypeDeclarationSyntax type => type.Identifier.Text,
                    MethodDeclarationSyntax method => method.Identifier.Text, ConstructorDeclarationSyntax constructor => constructor.Identifier.Text,
                    PropertyDeclarationSyntax property => property.Identifier.Text, _ => null };
                var span = node.GetLocation().GetLineSpan();
                return name == null ? null : new { name, kind = node.Kind().ToString(), line = span.StartLinePosition.Line + 1, end_line = span.EndLinePosition.Line + 1 };
            }).Where(item => item != null).ToArray();
            return new { symbols, has_syntax_errors = syntax.GetDiagnostics().Any(d => d.Severity == DiagnosticSeverity.Error), analysis = "Roslyn syntax" };
        }
        int reparsed = 0, rebuilt = 0;
        foreach (var input in request.GetProperty("projects").EnumerateArray())
        {
            string id = Text(input, "id"), version = Text(input, "version");
            if (!projects.TryGetValue(id, out var state)) projects[id] = state = new ProjectState();
            order.Remove(id); order.Add(id);
            if (state.Version == version) continue;
            var defines = input.GetProperty("defines").EnumerateArray().Select(item => item.GetString()!).ToArray();
            string parseVersion = string.Join(";", defines);
            var options = new CSharpParseOptions(preprocessorSymbols: defines);
            var current = new HashSet<string>();
            foreach (var file in input.GetProperty("files").EnumerateArray())
            {
                string path = Text(file, "path"), hash = Text(file, "version"); current.Add(path);
                if (state.ParseVersion == parseVersion && state.Trees.TryGetValue(path, out var old) && old.Version == hash) continue;
                state.Trees[path] = (hash, CSharpSyntaxTree.ParseText(Text(file, "content"), options, path)); reparsed++;
            }
            foreach (string removed in state.Trees.Keys.Except(current).ToArray()) state.Trees.Remove(removed);
            var refs = framework.Cast<MetadataReference>().ToList();
            foreach (var reference in input.GetProperty("references").EnumerateArray())
                refs.Add(MetadataReference.CreateFromFile(reference.GetString()!));
            foreach (var dependency in input.GetProperty("project_references").EnumerateArray())
                if (projects.TryGetValue(dependency.GetString()!, out var other)) refs.Add(other.Compilation.ToMetadataReference());
            state.Compilation = CSharpCompilation.Create(Path.GetFileNameWithoutExtension(id), state.Trees.Values.Select(item => item.Tree), refs,
                new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary, allowUnsafe: true));
            state.Version = version; state.ParseVersion = parseVersion; rebuilt++;
            // 索引会在任一项目版本变化时更新；复用没有变化的语法树。
            state.Calls = new();
            foreach (var tree in state.Compilation.SyntaxTrees)
            {
                var model = state.Compilation.GetSemanticModel(tree);
                foreach (var node in tree.GetRoot().DescendantNodes().Where(n => n is InvocationExpressionSyntax or ObjectCreationExpressionSyntax))
                {
                    var info = model.GetSymbolInfo(node);
                    state.Calls.Add((node, info.Symbol as IMethodSymbol, info, model));
                }
            }
        }
        while (order.Count > 24) { projects.Remove(order[0]); order.RemoveAt(0); }
        var selected = projects[Text(request, "project")];
        var source = selected.Trees[Text(request, "path")].Tree;
        int line = request.GetProperty("line").GetInt32() - 1;
        var root = source.GetRoot();
        var declaration = root.DescendantNodes().Where(n => n is BaseMethodDeclarationSyntax or AccessorDeclarationSyntax or LocalFunctionStatementSyntax or PropertyDeclarationSyntax)
            .Where(n => { var span = n.GetLocation().GetLineSpan(); return span.StartLinePosition.Line <= line && line <= span.EndLinePosition.Line; })
            .OrderBy(n => n.Span.Length).FirstOrDefault();
        var semantic = selected.Compilation.GetSemanticModel(source);
        var method = declaration == null ? null : semantic.GetDeclaredSymbol(declaration) as IMethodSymbol;
        var calls = selected.Calls.Where(item => declaration != null && item.Node.SyntaxTree == source && declaration.Span.Contains(item.Node.Span)).Take(50).Select(item => {
            var span = item.Node.GetLocation().GetLineSpan();
            bool deferred = item.Node.Ancestors().TakeWhile(n => n != declaration).Any(n => n is AnonymousFunctionExpressionSyntax or LocalFunctionStatementSyntax);
            var implementations = new List<object>();
            if (item.Target?.ContainingType.TypeKind == TypeKind.Interface)
                foreach (var tree in selected.Compilation.SyntaxTrees)
                    foreach (var type in tree.GetRoot().DescendantNodes().OfType<TypeDeclarationSyntax>())
                        if (selected.Compilation.GetSemanticModel(tree).GetDeclaredSymbol(type) is INamedTypeSymbol named && named.FindImplementationForInterfaceMember(item.Target) is { } implementation)
                            implementations.Add(Location(implementation));
            return new { path = span.Path, line = span.StartLinePosition.Line + 1, expression = item.Node.ToString(),
                resolved = item.Target != null, target = item.Target == null ? null : Location(item.Target),
                candidates = item.Info.CandidateSymbols.Take(8).Select(Location).ToArray(), reason = item.Info.CandidateReason.ToString(),
                deferred, possible_implementations = implementations.Take(20).ToArray(),
                dispatch = item.Target?.ContainingType.TypeKind == TypeKind.Interface ? "interface: possible implementations are not runtime proof" : "static binding" };
        }).ToArray();
        var loaded = request.GetProperty("projects").EnumerateArray().Select(p => projects[Text(p, "id")]);
        var callers = loaded.SelectMany(state => state.Calls).Where(item => Same(item.Target, method)).Take(30).Select(item => {
            var span = item.Node.GetLocation().GetLineSpan(); var owner = item.Model.GetEnclosingSymbol(item.Node.SpanStart);
            return new { path = span.Path, line = span.StartLinePosition.Line + 1, caller = owner == null ? null : Location(owner) };
        }).ToArray();
        var diagnostics = selected.Compilation.GetDiagnostics().Where(d => d.Severity == DiagnosticSeverity.Error).Take(20).Select(d => new { code = d.Id, message = d.GetMessage() }).ToArray();
        var branches = declaration?.DescendantNodes().Where(n => n is IfStatementSyntax or ReturnStatementSyntax or ThrowStatementSyntax or CatchClauseSyntax)
            .Take(40).Select(n => new { kind = n.Kind().ToString(), line = n.GetLocation().GetLineSpan().StartLinePosition.Line + 1,
                text = n is IfStatementSyntax branch ? branch.Condition.ToString() : n.ToString()[..Math.Min(250, n.ToString().Length)] }).ToArray();
        return new { analysis = "Roslyn semantic binding", symbol = method == null ? null : Location(method), calls, callers,
            callers_scope = "loaded project and project references only", control_flow = branches,
            diagnostics, completeness = diagnostics.Length == 0 ? "resolved within loaded project" : "partial: unresolved dependencies or compilation errors",
            stats = new { reparsed_files = reparsed, rebuilt_projects = rebuilt, indexed_files = selected.Trees.Count } };
    }
}
