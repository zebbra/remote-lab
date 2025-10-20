# Your project documentation


## Next steps

If you want to include this documentation as a sub-documentation in another repository, add the following line
to the `mkdocs_custom.yml` of the **other** repository.

```shell
cd submodules
git submodule add your-repo-name
```

```yaml
- Your project documentation: '!include ./submodules/your-repo-name/mkdocs.yml'
```

## Reference

- [Markdown/Material for MkDocs](https://squidfunk.github.io/mkdocs-material/reference/)
- [Usage of Snippets](https://facelessuser.github.io/pymdown-extensions/extensions/snippets/)
