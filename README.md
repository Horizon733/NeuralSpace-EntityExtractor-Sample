<h1 align="center">Entity Extractor Rasa custom component - NeuralSpace</h1>

## Instructions:
- Get your Access Token from <a href="https://platform.neuralspace.ai/#/platform/ner/dashboard">NeuralSpace platform</a>
- ![image](https://user-images.githubusercontent.com/57827233/159902159-8394159c-57b5-47a3-8ec0-75a4464190f1.png)

### Rasa 2.x
- Make sure your project is using `2.x` version of `Rasa`.
- Use `rasa-2.x` branch for Entity extractor.
- Add following code in `config.yml`.
```yml
policies:
  ...
  - name: custom_component.NeuralspaceEntityExtractor.NeuralSpaceEntityExtractor
    language: "en" # source language of the sentences
    dimensions: [ "person", "email", "number" ] # dimensions you want to extract entity
    access_token: "your-access-token" # find your access token from NeuralSpace Platform as above mentioned.
  ...
```

### Rasa 3.x
- Make sure you have migrated/using `3.x` version of `Rasa`.
- Use `rasa-3.x` branch for Entity extractor.
- Add following code in `config.yml`.
```yml
recipe: default.v1
language: en
policies:
  ...
  - name: custom_component.NeuralspaceEntityExtractor.NeuralSpaceEntityExtractor
    language: "en" # source language of the sentences
    dimensions: [ "person", "email", "number" ] # dimensions you want to extract entity
    access_token: "your-access-token" # find your access token from NeuralSpace Platform as above mentioned.
  ...
```

## Found this helpful?
Support me by<br><br>
- <a href="https://www.buymeacoffee.com/droidcity0" target="_blank">
  <img width="200" alt="yellow-button" src="https://user-images.githubusercontent.com/57827233/159906809-2687436d-d91c-411f-bb37-ef9c78acf53b.png">
</a>
- Give a 🌟 to this repo
