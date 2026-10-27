# .NET / Razor / SQL Server optional pack

Discover a `.sln` or `.slnx` and actual SDK version first. Recommended validation on a trusted project: `dotnet restore`, `dotnet build --no-restore`, `dotnet test --no-build`. Do not apply SQL migrations or `DROP` to user DBs automatically. Review EF migration and backup before writes. Treat secrets, connection strings, and tenant IDs as restricted.
